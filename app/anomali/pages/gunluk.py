import streamlit as st
import pandas as pd
from db import get_conn
from components.grafik import candlestick_goster

ESIK_SKOR = 4.5

RZ60_RENK  = "#d4820a"
RZ120_RENK = "#22c55e"


def _sec_header(n, title, sub=""):
    sub_html = f' <span style="color:#2e2e48;font-size:10px">{sub}</span>' if sub else ""
    st.markdown(
        f'<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;'
        f'margin:20px 0 14px 0">'
        f'<span style="color:#2e2e48;margin-right:8px">§ {n}</span>{title}{sub_html}</div>',
        unsafe_allow_html=True,
    )


def _agrege(df):
    rows = []
    for hisse, grp in df.groupby("hisse_kodu", sort=False):
        r60  = grp[grp["anomali_tipi"] == "anomali_rz60"].iloc[0]  if len(grp[grp["anomali_tipi"] == "anomali_rz60"])  > 0 else None
        r120 = grp[grp["anomali_tipi"] == "anomali_rz120"].iloc[0] if len(grp[grp["anomali_tipi"] == "anomali_rz120"]) > 0 else None
        max_skor = grp["skor"].max()
        durumlar = grp["durum"].tolist()
        durum = "beklemede" if "beklemede" in durumlar else (durumlar[0] if durumlar else "")
        rows.append({
            "hisse_kodu":    hisse,
            "rz60_id":       r60["id"]           if r60  is not None else None,
            "rz60_skor":     float(r60["skor"])   if r60  is not None else None,
            "rz60_durum":    r60["durum"]          if r60  is not None else None,
            "rz60_notlar":   r60.get("notlar")     if r60  is not None else None,
            "rz60_zaman":    r60["baslangic_zaman"] if r60 is not None else None,
            "rz120_id":      r120["id"]            if r120 is not None else None,
            "rz120_skor":    float(r120["skor"])   if r120 is not None else None,
            "rz120_durum":   r120["durum"]         if r120 is not None else None,
            "rz120_notlar":  r120.get("notlar")    if r120 is not None else None,
            "rz120_zaman":   r120["baslangic_zaman"] if r120 is not None else None,
            "max_skor":      max_skor,
            "durum":         durum,
            "has_both":      r60 is not None and r120 is not None,
        })
    return sorted(rows, key=lambda x: -x["max_skor"])


def _detay_panel(satir, conn):
    stock_id_df = pd.read_sql(
        "SELECT id FROM stocks WHERE symbol = %s", conn, params=(satir["hisse_kodu"],)
    )
    if stock_id_df.empty:
        return
    stock_id = int(stock_id_df["id"].iloc[0])

    anomali_rows = []
    if satir["rz60_id"] is not None:
        anomali_rows.append(("RZ60",  RZ60_RENK,  satir["rz60_id"],
                             satir["rz60_skor"],  satir["rz60_durum"],
                             satir["rz60_notlar"], satir["rz60_zaman"]))
    if satir["rz120_id"] is not None:
        anomali_rows.append(("RZ120", RZ120_RENK, satir["rz120_id"],
                             satir["rz120_skor"], satir["rz120_durum"],
                             satir["rz120_notlar"], satir["rz120_zaman"]))

    ref_zaman = satir["rz60_zaman"] or satir["rz120_zaman"]

    badges_html = ""
    for tip, renk, _, askor, adurum, _, _ in anomali_rows:
        dr = {"beklemede": "#d4820a", "onaylandi": "#e84040", "ret": "#22c55e"}.get(adurum, "#3a3a55")
        badges_html += (
            f'<span style="border:1px solid {renk};color:{renk};font-size:10px;'
            f'padding:1px 6px;border-radius:2px;margin-right:6px">{tip}</span>'
            f'<span style="font-size:12px;color:#e0e0f0;margin-right:12px">{askor:.4f}</span>'
            f'<span style="font-size:10px;color:{dr};margin-right:20px">{adurum}</span>'
        )
    st.markdown(
        f'<div style="background:#0d0d1a;border:1px solid #1a1a24;border-radius:2px;'
        f'padding:10px 14px;margin-bottom:12px;display:flex;align-items:center;gap:8px">'
        f'<span style="font-size:14px;color:#e0e0f0;font-weight:400;margin-right:16px">'
        f'{satir["hisse_kodu"]}</span>'
        f'<span style="font-size:10px;color:#3a3a55;margin-right:16px">'
        f'{str(ref_zaman)[:10]}</span>'
        f'{badges_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    col_g, col_z, col_k = st.columns([5, 3, 3])

    with col_g:
        st.markdown(
            '<div style="font-size:9px;color:#2e2e48;letter-spacing:0.1em;'
            'text-transform:uppercase;margin-bottom:6px">Fiyat + Hacim · 25g</div>',
            unsafe_allow_html=True,
        )
        df_fiyat = pd.read_sql("""
            SELECT price_date AS zaman, open_price AS acilis, high_price AS yuksek,
                   low_price AS dusuk, close_price AS kapanis, volume AS hacim
            FROM stock_prices
            WHERE stock_id = %s
              AND price_date BETWEEN %s::date - interval '20 days'
                                 AND %s::date + interval '5 days'
            ORDER BY price_date
        """, conn, params=(stock_id, ref_zaman, ref_zaman))
        if not df_fiyat.empty:
            candlestick_goster(df_fiyat, key=f"g_{satir['hisse_kodu']}", yukseklik=190)
        else:
            st.markdown('<div style="font-size:10px;color:#2e2e48">Fiyat verisi yok.</div>',
                        unsafe_allow_html=True)

    with col_z:
        st.markdown(
            '<div style="font-size:9px;color:#2e2e48;letter-spacing:0.1em;'
            'text-transform:uppercase;margin-bottom:6px">Son 10 Gün · Z-Değerleri</div>',
            unsafe_allow_html=True,
        )
        df_z = pd.read_sql("""
            SELECT price_date, z_score_robust_60, z_score_robust_120
            FROM volume_analysis
            WHERE stock_id = %s
              AND price_date <= %s::date
            ORDER BY price_date DESC
            LIMIT 10
        """, conn, params=(stock_id, ref_zaman))

        if not df_z.empty:
            def _zr(v):
                av = abs(float(v)) if pd.notna(v) else 0
                if av >= 3: return "#e84040"
                if av >= 2: return "#d4820a"
                return "#4a4a68"

            st.markdown(
                '<div style="display:grid;grid-template-columns:80px 58px 62px;gap:0;'
                'padding:5px 8px;border-bottom:1px solid #1a1a24;'
                'font-size:9px;color:#2e2e48;letter-spacing:0.08em;text-transform:uppercase">'
                '<span>Tarih</span><span>RZ60</span><span>RZ120</span></div>',
                unsafe_allow_html=True,
            )
            for _, zrow in df_z.iterrows():
                rz60v  = float(zrow["z_score_robust_60"])  if pd.notna(zrow["z_score_robust_60"])  else None
                rz120v = float(zrow["z_score_robust_120"]) if pd.notna(zrow["z_score_robust_120"]) else None
                rz60_str  = f"{rz60v:.3f}"  if rz60v  is not None else "—"
                rz120_str = f"{rz120v:.3f}" if rz120v is not None else "—"
                is_anom = str(zrow["price_date"])[:10] == str(ref_zaman)[:10]
                bg = "background:#131320;" if is_anom else ""
                date_renk = "#e0e0f0" if is_anom else "#3a3a55"
                st.markdown(
                    f'<div style="display:grid;grid-template-columns:80px 58px 62px;gap:0;'
                    f'padding:6px 8px;border-bottom:1px solid #0f0f18;{bg}">'
                    f'<span style="font-size:10px;color:{date_renk}">'
                    f'{str(zrow["price_date"])[:10]}</span>'
                    f'<span style="font-size:10px;color:{_zr(rz60v)}">{rz60_str}</span>'
                    f'<span style="font-size:10px;color:{_zr(rz120v)}">{rz120_str}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div style="font-size:10px;color:#2e2e48">Z-Score verisi yok.</div>',
                        unsafe_allow_html=True)

    with col_k:
        st.markdown(
            '<div style="font-size:9px;color:#2e2e48;letter-spacing:0.1em;'
            'text-transform:uppercase;margin-bottom:6px">Karar</div>',
            unsafe_allow_html=True,
        )
        neden_html = ""
        for tip, renk, _, askor, _, _, _ in anomali_rows:
            neden_html += (
                f'<div style="font-size:10px;color:#4a4a68;margin-bottom:3px">'
                f'<span style="color:{renk}">{tip}</span>'
                f' = <span style="color:#e0e0f0">{askor:.4f}</span>'
                f' &gt; eşik <span style="color:#4a4a68">{ESIK_SKOR}</span></div>'
            )
        st.markdown(
            f'<div style="background:#0d0d1a;border:1px solid #1a1a24;border-radius:2px;'
            f'padding:10px 12px;margin-bottom:10px">'
            f'<div style="font-size:9px;color:#2e2e48;letter-spacing:0.08em;'
            f'text-transform:uppercase;margin-bottom:6px">Neden Anomali</div>'
            f'{neden_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

        for tip, renk, aid, askor, adurum, anotlar, _ in anomali_rows:
            not_metni = st.text_area(
                f"not_{tip}", value=anotlar or "",
                key=f"not_{aid}", height=52,
                label_visibility="collapsed",
                placeholder=f"{tip} notu (opsiyonel)",
            )
            c1, c2 = st.columns(2)
            if c1.button(f"ONAYLA {tip}", key=f"onayla_{aid}", type="primary"):
                cur = conn.cursor()
                cur.execute(
                    "UPDATE anomali_kayitlari SET durum='onaylandi', notlar=%s WHERE id=%s",
                    (not_metni, aid),
                )
                conn.commit(); cur.close()
                st.success(f"{tip} onaylandı."); st.rerun()
            if c2.button(f"REDDET {tip}", key=f"reddet_{aid}"):
                cur = conn.cursor()
                cur.execute(
                    "UPDATE anomali_kayitlari SET durum='ret', notlar=%s WHERE id=%s",
                    (not_metni, aid),
                )
                conn.commit(); cur.close()
                st.success(f"{tip} reddedildi."); st.rerun()
            st.markdown("<div style='margin-bottom:6px'></div>", unsafe_allow_html=True)


def _liste_goster(hisseler, conn):
    for satir in hisseler:
        rz60_str  = f"RZ60 {satir['rz60_skor']:.4f}"  if satir["rz60_skor"]  is not None else ""
        rz120_str = f"RZ120 {satir['rz120_skor']:.4f}" if satir["rz120_skor"] is not None else ""
        skorlar   = "   ·   ".join(filter(None, [rz60_str, rz120_str]))
        label     = f"{satir['hisse_kodu']}   {skorlar}   {satir['durum']}"

        with st.expander(label, expanded=False):
            _detay_panel(satir, conn)


def goster():
    conn = get_conn()

    son_tarih_df = pd.read_sql(
        "SELECT DATE(baslangic_zaman) AS gun FROM anomali_kayitlari ORDER BY gun DESC LIMIT 1",
        conn,
    )
    if son_tarih_df.empty:
        st.info("Henüz anomali kaydı yok.")
        return
    son_tarih = son_tarih_df.iloc[0]["gun"]

    df = pd.read_sql("""
        SELECT id, hisse_kodu, anomali_tipi, skor, durum, notlar, baslangic_zaman
        FROM anomali_kayitlari
        WHERE DATE(baslangic_zaman) = %s
          AND anomali_tipi IN ('anomali_rz60', 'anomali_rz120')
        ORDER BY skor DESC
    """, conn, params=(str(son_tarih),))

    if df.empty:
        st.markdown(
            '<div style="font-size:11px;color:#2e2e48;padding:24px;'
            'border:1px solid #1a1a24;border-radius:2px;text-align:center">'
            'Bu gün için Robust Z anomalisi bulunamadı.</div>',
            unsafe_allow_html=True,
        )
        return

    hisseler = _agrege(df)

    _sec_header(1, "Günlük Robust Z Raporu", f"· {son_tarih}")

    kritik = [h for h in hisseler if h["max_skor"] > ESIK_SKOR]
    kart_hisse = len(kritik)
    kart_bekl  = sum(1 for h in kritik if h["durum"] == "beklemede")

    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, renk in [
        (c1, f"Hisse  (>{ESIK_SKOR})",  kart_hisse,  "#e0e0f0"),
        (c2, "Beklemede",               kart_bekl,   "#d4820a"),
        (c3, "Toplam Hisse",            len(hisseler),"#4a4a68"),
        (c4, "Eşik",                    ESIK_SKOR,   "#4a4a68"),
    ]:
        col.markdown(
            f'<div style="background:#0f0f18;border:1px solid #1a1a24;'
            f'border-radius:2px;padding:12px 14px;margin-bottom:8px">'
            f'<div style="font-size:9px;color:#2e2e48;letter-spacing:0.12em;'
            f'text-transform:uppercase;margin-bottom:4px">{label}</div>'
            f'<div style="font-size:22px;color:{renk};font-weight:300">{val}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    col_baslik, col_filtre = st.columns([3, 6])
    with col_baslik:
        ortak_n = sum(1 for h in hisseler if h["has_both"])
        _sec_header(2, "Hisse Listesi",
                    f"· {len(hisseler)} hisse · {ortak_n} ortak")
    with col_filtre:
        secim = st.radio(
            "tip", ["Hepsi", "RZ60", "RZ120", "Ortak"],
            horizontal=True, label_visibility="collapsed",
            key="gunluk_tip_filtre",
        )

    if secim == "Ortak":
        liste = [h for h in hisseler if h["has_both"]]
    elif secim == "RZ60":
        liste = [h for h in hisseler if h["rz60_skor"] is not None]
    elif secim == "RZ120":
        liste = [h for h in hisseler if h["rz120_skor"] is not None]
    else:
        liste = hisseler

    if not liste:
        st.markdown(
            '<div style="font-size:11px;color:#2e2e48;padding:14px;'
            'border:1px solid #1a1a24;border-radius:2px">Bu filtrede kayıt yok.</div>',
            unsafe_allow_html=True,
        )
    else:
        _liste_goster(liste, conn)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("YENİLE", key="gunluk_yenile"):
        st.cache_resource.clear()
        st.cache_data.clear()
        st.rerun()
