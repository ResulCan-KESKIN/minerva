import streamlit as st
import pandas as pd
from db import get_conn


def _sec_header(n, title):
    st.markdown(
        f'<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;'
        f'margin:20px 0 14px 0">'
        f'<span style="color:#2e2e48;margin-right:8px">§ {n}</span>{title}</div>',
        unsafe_allow_html=True,
    )


def goster():
    conn = get_conn()

    _sec_header(1, "Özet Metrikler")

    ozet = pd.read_sql("""
        SELECT
            COUNT(DISTINCT hisse_kodu) as hisse_sayisi,
            COUNT(*) as toplam_anomali,
            COUNT(*) FILTER (WHERE durum = 'beklemede') as beklemede,
            COUNT(*) FILTER (WHERE durum = 'onaylandi') as onaylandi
        FROM anomali_kayitlari
    """, conn)

    r = ozet.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, renk in [
        (c1, "Takip Edilen",  int(r["hisse_sayisi"]),    "#e0e0f0"),
        (c2, "Toplam Anomali", int(r["toplam_anomali"]), "#e0e0f0"),
        (c3, "Beklemede",      int(r["beklemede"]),      "#d4820a"),
        (c4, "Onaylandi",      int(r["onaylandi"]),      "#e84040"),
    ]:
        col.markdown(
            f'<div style="background:#0f0f18;border:1px solid #1a1a24;'
            f'border-radius:2px;padding:14px 16px;margin-bottom:20px">'
            f'<div style="font-size:9px;color:#3a3a55;letter-spacing:0.12em;'
            f'text-transform:uppercase;margin-bottom:6px">{label}</div>'
            f'<div style="font-size:26px;color:{renk};font-weight:300">{val:,}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _sec_header(2, "Hisse Bazlı Anomali Özeti")

    hisse_ozet = pd.read_sql("""
        SELECT
            hisse_kodu,
            COUNT(*) as toplam,
            COUNT(*) FILTER (WHERE durum = 'beklemede') as beklemede,
            COUNT(*) FILTER (WHERE durum = 'onaylandi') as onaylandi,
            MAX(skor) as max_skor,
            MAX(baslangic_zaman)::date as son_anomali
        FROM anomali_kayitlari
        GROUP BY hisse_kodu
        ORDER BY toplam DESC
    """, conn)

    st.markdown(
        '<div style="display:grid;grid-template-columns:120px 70px 80px 70px 90px 110px;'
        'gap:0;padding:7px 14px;border-bottom:1px solid #1a1a24;'
        'font-size:9px;color:#2e2e48;letter-spacing:0.12em;text-transform:uppercase">'
        '<span>Hisse</span><span>Toplam</span><span>Beklemede</span>'
        '<span>Onayli</span><span>Max Skor</span><span>Son Anomali</span></div>',
        unsafe_allow_html=True,
    )

    for _, row in hisse_ozet.iterrows():
        st.markdown(
            f'<div style="display:grid;grid-template-columns:120px 70px 80px 70px 90px 110px;'
            f'gap:0;padding:9px 14px;border-bottom:1px solid #0f0f18;'
            f'align-items:center">'
            f'<span style="font-size:12px;color:#e0e0f0">{row["hisse_kodu"]}</span>'
            f'<span style="font-size:11px;color:#8888a8">{int(row["toplam"])}</span>'
            f'<span style="font-size:11px;color:#d4820a">{int(row["beklemede"])}</span>'
            f'<span style="font-size:11px;color:#e84040">{int(row["onaylandi"])}</span>'
            f'<span style="font-size:11px;color:#4a4a68">{row["max_skor"]:.4f}</span>'
            f'<span style="font-size:11px;color:#4a4a68">{str(row["son_anomali"])}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
