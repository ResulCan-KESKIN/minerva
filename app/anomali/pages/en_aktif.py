import streamlit as st
import pandas as pd
from db import get_conn


PERIOD_SQL = {
    "7 Gün":  "NOW() - INTERVAL '7 days'",
    "30 Gün": "NOW() - INTERVAL '30 days'",
    "90 Gün": "NOW() - INTERVAL '90 days'",
    "Tümü":   "'-infinity'::timestamptz",
}

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


def goster():
    conn = get_conn()

    col_baslik, col_filtre = st.columns([3, 5])
    with col_baslik:
        _sec_header(1, "En Aktif Hisseler")
    with col_filtre:
        donem = st.radio(
            "donem",
            list(PERIOD_SQL.keys()),
            index=1,
            horizontal=True,
            label_visibility="collapsed",
            key="en_aktif_donem",
        )

    since_sql = PERIOD_SQL[donem]

    ozet = pd.read_sql(f"""
        SELECT
            COUNT(DISTINCT hisse_kodu)                             AS hisse_sayisi,
            COUNT(*)                                               AS toplam_alarm,
            COUNT(*) FILTER (WHERE durum = 'beklemede')            AS beklemede,
            COUNT(*) FILTER (WHERE durum = 'onaylandi')            AS onaylandi
        FROM anomali_kayitlari
        WHERE baslangic_zaman >= {since_sql}
          AND anomali_tipi IN ('anomali_rz60', 'anomali_rz120')
    """, conn).iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, renk in [
        (c1, f"Aktif Hisse · {donem}",  int(ozet["hisse_sayisi"]), "#e0e0f0"),
        (c2, "Toplam Alarm",            int(ozet["toplam_alarm"]), "#e0e0f0"),
        (c3, "Beklemede",               int(ozet["beklemede"]),    "#d4820a"),
        (c4, "Onaylı",                  int(ozet["onaylandi"]),    "#e84040"),
    ]:
        col.markdown(
            f'<div style="background:#0f0f18;border:1px solid #1a1a24;'
            f'border-radius:2px;padding:12px 14px;margin-bottom:16px">'
            f'<div style="font-size:9px;color:#2e2e48;letter-spacing:0.12em;'
            f'text-transform:uppercase;margin-bottom:4px">{label}</div>'
            f'<div style="font-size:22px;color:{renk};font-weight:300">{val:,}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    df = pd.read_sql(f"""
        SELECT
            hisse_kodu,
            COUNT(*)                                               AS toplam,
            COUNT(*) FILTER (WHERE anomali_tipi = 'anomali_rz60')  AS rz60,
            COUNT(*) FILTER (WHERE anomali_tipi = 'anomali_rz120') AS rz120,
            COUNT(*) FILTER (WHERE durum = 'beklemede')            AS beklemede,
            COUNT(*) FILTER (WHERE durum = 'onaylandi')            AS onaylandi,
            ROUND(MAX(skor)::numeric, 4)                           AS max_skor,
            MAX(baslangic_zaman)::date                             AS son_tarih,
            MIN(baslangic_zaman)::date                             AS ilk_tarih
        FROM anomali_kayitlari
        WHERE baslangic_zaman >= {since_sql}
          AND anomali_tipi IN ('anomali_rz60', 'anomali_rz120')
        GROUP BY hisse_kodu
        ORDER BY toplam DESC, max_skor DESC
    """, conn)

    if df.empty:
        st.markdown(
            '<div style="font-size:11px;color:#2e2e48;padding:24px;'
            'border:1px solid #1a1a24;border-radius:2px;text-align:center">'
            'Seçili dönemde anomali kaydı bulunamadı.</div>',
            unsafe_allow_html=True,
        )
        return

    _sec_header(2, "Hisse Sıralaması", f"· {len(df)} hisse")

    st.markdown(
        '<div style="display:grid;'
        'grid-template-columns:38px 100px 1fr 64px 64px 72px 64px 90px 88px 88px;'
        'gap:0;padding:6px 14px;border-bottom:1px solid #1a1a24;'
        'font-size:9px;color:#2e2e48;letter-spacing:0.1em;text-transform:uppercase">'
        '<span>#</span>'
        '<span>Hisse</span>'
        '<span>Dağılım</span>'
        '<span>Toplam</span>'
        '<span style="color:#d4820a">RZ60</span>'
        '<span style="color:#22c55e">RZ120</span>'
        '<span>Bekl.</span>'
        '<span>Onaylı</span>'
        '<span>Max Skor</span>'
        '<span>Son Alarm</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    max_toplam = int(df["toplam"].max()) or 1

    for rank, row in enumerate(df.itertuples(index=False), start=1):
        toplam   = int(row.toplam)
        rz60_n   = int(row.rz60)
        rz120_n  = int(row.rz120)
        bekl_n   = int(row.beklemede)
        onayli_n = int(row.onaylandi)
        max_skor = float(row.max_skor)

        bar_total = 120
        rz60_w  = int(rz60_n  / max_toplam * bar_total)
        rz120_w = int(rz120_n / max_toplam * bar_total)
        bar_html = (
            f'<div style="display:flex;align-items:center;gap:1px">'
            f'<div style="width:{rz60_w}px;height:6px;background:#d4820a;border-radius:1px 0 0 1px"></div>'
            f'<div style="width:{rz120_w}px;height:6px;background:#22c55e;border-radius:0 1px 1px 0"></div>'
            f'</div>'
        )

        bekl_renk   = "#d4820a" if bekl_n   > 0 else "#2e2e48"
        onayli_renk = "#e84040" if onayli_n > 0 else "#2e2e48"
        bg = "background:#0d0d1a;" if rank % 2 == 0 else ""

        rank_renk = {1: "#e0e0f0", 2: "#8888a8", 3: "#6a6a88"}.get(rank, "#2e2e48")

        st.markdown(
            f'<div style="display:grid;'
            f'grid-template-columns:38px 100px 1fr 64px 64px 72px 64px 90px 88px 88px;'
            f'gap:0;padding:9px 14px;border-bottom:1px solid #0a0a12;{bg}align-items:center">'
            f'<span style="font-size:10px;color:{rank_renk}">{rank}</span>'
            f'<span style="font-size:12px;color:#e0e0f0">{row.hisse_kodu}</span>'
            f'<span>{bar_html}</span>'
            f'<span style="font-size:11px;color:#8888a8">{toplam}</span>'
            f'<span style="font-size:11px;color:#d4820a">{rz60_n}</span>'
            f'<span style="font-size:11px;color:#22c55e">{rz120_n}</span>'
            f'<span style="font-size:11px;color:{bekl_renk}">{bekl_n}</span>'
            f'<span style="font-size:11px;color:{onayli_renk}">{onayli_n}</span>'
            f'<span style="font-size:11px;color:#8888a8">{max_skor:.4f}</span>'
            f'<span style="font-size:10px;color:#4a4a68">{str(row.son_tarih)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("YENİLE", key="en_aktif_yenile"):
        st.cache_data.clear()
        st.rerun()
