import streamlit as st
import pandas as pd
from datetime import timedelta
from db import get_conn
from components.grafik import candlestick_goster
from components.anomali_tablo import tip_badge, durum_badge
from components.zscore_panel import zscore_panel_goster


PERIODS = {"1A": 30, "3A": 90, "6A": 180, "1Y": 365, "TÜM": None}


def goster(secilen):
    conn = get_conn()

    id_df = pd.read_sql("SELECT id FROM stocks WHERE symbol = %s", conn, params=(secilen,))
    if id_df.empty:
        st.warning(f"{secilen} bulunamadı.")
        return
    stock_id = int(id_df["id"].iloc[0])

    df_fiyat = pd.read_sql("""
        SELECT price_date AS zaman, open_price AS acilis, high_price AS yuksek,
               low_price AS dusuk, close_price AS kapanis, volume AS hacim
        FROM stock_prices WHERE stock_id = %s ORDER BY price_date
    """, conn, params=(stock_id,))

    anomaliler = pd.read_sql("""
        SELECT id, baslangic_zaman, anomali_tipi, ROUND(skor::numeric,4) AS skor, durum
        FROM anomali_kayitlari WHERE hisse_kodu = %s ORDER BY skor DESC
    """, conn, params=(secilen,))

    zscore_df = pd.read_sql("""
        SELECT price_date AS tarih, z_score_60, z_score_120,
               z_score_robust_60, z_score_robust_120
        FROM volume_analysis WHERE stock_id = %s ORDER BY price_date
    """, conn, params=(stock_id,))

    veri_gun   = len(zscore_df)
    ilk_tarih  = df_fiyat["zaman"].min() if not df_fiyat.empty else "—"
    son_tarih  = df_fiyat["zaman"].max() if not df_fiyat.empty else "—"
    toplam_a   = len(anomaliler)
    beklemede_a= int((anomaliler["durum"] == "beklemede").sum()) if not anomaliler.empty else 0
    min_z      = float(anomaliler["skor"].min()) if not anomaliler.empty else 0.0

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    for col, label, val, renk in [
        (m1, "Veri",      f"{veri_gun}g",                             "#e0e0f0"),
        (m2, "İlk",       str(ilk_tarih)[:10] if ilk_tarih != "—" else "—", "#8888a8"),
        (m3, "Son",       str(son_tarih)[:10] if son_tarih != "—" else "—", "#8888a8"),
        (m4, "Toplam",    toplam_a,                                   "#8888a8"),
        (m5, "Beklemede", beklemede_a,                                "#d4820a"),
        (m6, "Min |Z|",   f"{min_z:.4f}",                            "#4a4a68"),
    ]:
        col.markdown(
            f'<div style="background:#0f0f18;border:1px solid #1a1a24;'
            f'border-radius:2px;padding:10px 12px;margin-bottom:12px">'
            f'<div style="font-size:9px;color:#2e2e48;letter-spacing:0.12em;'
            f'text-transform:uppercase;margin-bottom:4px">{label}</div>'
            f'<div style="font-size:16px;color:{renk};font-weight:300">{val}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    col_main, col_side = st.columns([13, 7], gap="large")

    with col_main:
        row_baslik, row_period = st.columns([4, 4])
        with row_baslik:
            st.markdown(
                '<div style="font-size:10px;color:#2a2a40;letter-spacing:0.1em;'
                'text-transform:uppercase;padding-top:8px">'
                '§ 1 &nbsp; Fiyat Grafiği + Hacim</div>',
                unsafe_allow_html=True,
            )
        with row_period:
            period_sec = st.radio(
                "period",
                list(PERIODS.keys()),
                horizontal=True,
                index=3,
                label_visibility="collapsed",
                key="hd_period",
            )

        gun = PERIODS[period_sec]
        if not df_fiyat.empty:
            df_fiyat["zaman"] = pd.to_datetime(df_fiyat["zaman"])
            if gun:
                cutoff = df_fiyat["zaman"].max() - timedelta(days=gun)
                df_filtered = df_fiyat[df_fiyat["zaman"] >= cutoff]
            else:
                df_filtered = df_fiyat

            anoms_filtered = anomaliler.copy()
            if gun and not anomaliler.empty:
                anoms_filtered["baslangic_zaman"] = pd.to_datetime(anoms_filtered["baslangic_zaman"])
                cutoff_a = df_fiyat["zaman"].max() - timedelta(days=gun)
                anoms_filtered = anoms_filtered[anoms_filtered["baslangic_zaman"] >= cutoff_a]

            candlestick_goster(df_filtered, anoms_filtered, key=f"chart_{secilen}_{period_sec}", yukseklik=340)

            if not zscore_df.empty:
                zscore_df["tarih"] = pd.to_datetime(zscore_df["tarih"])
                if gun:
                    zscore_df = zscore_df[zscore_df["tarih"] >= (zscore_df["tarih"].max() - timedelta(days=gun))]
                zscore_panel_goster(zscore_df)
        else:
            st.info("Fiyat verisi bulunamadı.")

    with col_side:
        st.markdown(
            f'<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;'
            f'margin:0 0 10px 0">'
            f'<span style="color:#2e2e48;margin-right:8px">§ 2</span>'
            f'Anomali Kayıtları'
            f'<span style="color:#2e2e48;font-size:10px;margin-left:8px">'
            f'· {toplam_a} kayıt</span></div>',
            unsafe_allow_html=True,
        )

        if anomaliler.empty:
            st.markdown(
                '<div style="font-size:11px;color:#2e2e48;padding:16px;'
                'border:1px solid #1a1a24;border-radius:2px">Kayıt yok.</div>',
                unsafe_allow_html=True,
            )
        else:
            sort_col = st.radio(
                "sort",
                ["Skor↓", "Tarih↓"],
                horizontal=True,
                label_visibility="collapsed",
                key="hd_sort",
            )
            if sort_col == "Tarih↓":
                anomaliler = anomaliler.sort_values("baslangic_zaman", ascending=False)
            else:
                anomaliler = anomaliler.sort_values("skor", ascending=False)

            st.markdown(
                '<div style="display:grid;grid-template-columns:88px 52px 64px 80px;'
                'gap:0;padding:6px 10px;border-bottom:1px solid #1a1a24;'
                'font-size:9px;color:#2e2e48;letter-spacing:0.1em;text-transform:uppercase">'
                '<span>Tarih</span><span>Tip</span><span>Skor</span><span>Durum</span></div>',
                unsafe_allow_html=True,
            )
            for _, row in anomaliler.iterrows():
                tarih = str(row["baslangic_zaman"])[:10]
                st.markdown(
                    f'<div style="display:grid;grid-template-columns:88px 52px 64px 80px;'
                    f'gap:0;padding:8px 10px;border-bottom:1px solid #0f0f18;align-items:center">'
                    f'<span style="font-size:10px;color:#8888a8">{tarih}</span>'
                    f'<span>{tip_badge(row["anomali_tipi"])}</span>'
                    f'<span style="font-size:10px;color:#4a4a68">{row["skor"]:.4f}</span>'
                    f'{durum_badge(row["durum"])}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
