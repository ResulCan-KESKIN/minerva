# pages/genel_bakis.py
import streamlit as st
import pandas as pd
from db import get_conn

def goster():
    conn = get_conn()

    st.markdown('<div style="font-size:10px;color:#666680;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:24px;padding-bottom:8px;border-bottom:1px solid #1e1e2e">Genel Bakis — Tum Hisseler</div>', unsafe_allow_html=True)

    # Özet metrikler
    ozet = pd.read_sql("""
        SELECT
            COUNT(DISTINCT hisse_kodu) as hisse_sayisi,
            COUNT(*) as toplam_anomali,
            COUNT(*) FILTER (WHERE durum = 'beklemede') as beklemede,
            COUNT(*) FILTER (WHERE durum = '🔴 onaylandi') as onaylandi
        FROM anomali_kayitlari
    """, conn)

    c1, c2, c3, c4 = st.columns(4)
    satirlar = ozet.iloc[0]

    for col, label, val, renk in [
        (c1, "Takip Edilen Hisse", int(satirlar["hisse_sayisi"]), "normal"),
        (c2, "Toplam Anomali",     int(satirlar["toplam_anomali"]), "normal"),
        (c3, "Beklemede",          int(satirlar["beklemede"]), "warn"),
        (c4, "Onaylandi",          int(satirlar["onaylandi"]), "danger"),
    ]:
        renkler = {"normal": "#ffffff", "warn": "#f59e0b", "danger": "#ef4444"}
        col.markdown(f"""
        <div style="background:#0f0f1a;border:1px solid #1e1e2e;border-radius:4px;
                    padding:16px 20px;margin-bottom:24px">
            <div style="font-size:10px;color:#666680;letter-spacing:0.12em;
                        text-transform:uppercase;margin-bottom:6px">{label}</div>
            <div style="font-family:IBM Plex Mono;font-size:28px;
                        color:{renkler[renk]}">{val}</div>
        </div>
        """, unsafe_allow_html=True)

    # Hisse bazlı anomali özeti
    st.markdown('<div style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:12px">Hisse Bazli Anomali Ozeti</div>', unsafe_allow_html=True)

    hisse_ozet = pd.read_sql("""
        SELECT
            hisse_kodu,
            COUNT(*) as toplam,
            COUNT(*) FILTER (WHERE durum = 'beklemede') as beklemede,
            COUNT(*) FILTER (WHERE durum = '🔴 onaylandi') as onaylandi,
            MIN(skor) as en_dusuk_skor,
            MAX(baslangic_zaman)::date as son_anomali
        FROM anomali_kayitlari
        GROUP BY hisse_kodu
        ORDER BY toplam DESC
    """, conn)

    st.markdown("""
    <div style="display:grid;grid-template-columns:130px 80px 80px 80px 100px 120px;gap:16px;
                padding:10px 16px;border-bottom:1px solid #1e1e2e;
                font-size:10px;color:#666680;letter-spacing:0.1em;text-transform:uppercase">
        <span>Hisse</span><span>Toplam</span><span>Beklemede</span>
        <span>Onaylandi</span><span>Min Skor</span><span>Son Anomali</span>
    </div>
    """, unsafe_allow_html=True)

    for _, row in hisse_ozet.iterrows():
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:130px 80px 80px 80px 100px 120px;gap:16px;
                    padding:12px 16px;border-bottom:1px solid #111120;align-items:center">
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#ffffff">{row['hisse_kodu']}</span>
            <span style="font-family:IBM Plex Mono;font-size:12px">{int(row['toplam'])}</span>
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#f59e0b">{int(row['beklemede'])}</span>
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#ef4444">{int(row['onaylandi'])}</span>
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#666680">{row['en_dusuk_skor']:.4f}</span>
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#666680">{str(row['son_anomali'])}</span>
        </div>
        """, unsafe_allow_html=True)
