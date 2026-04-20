import streamlit as st
import pandas as pd
from db import get_conn

def goster():
    conn = get_conn()

    st.markdown('<div style="font-size:10px;color:#666680;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:24px;padding-bottom:8px;border-bottom:1px solid #1e1e2e">Sistem Durumu</div>', unsafe_allow_html=True)

    # Son veri tarihleri
    son_veri = pd.read_sql("""
        SELECT hisse_kodu, MAX(zaman::date) as son_tarih, COUNT(*) as kayit_sayisi
        FROM hisse_fiyatlari
        GROUP BY hisse_kodu ORDER BY hisse_kodu
    """, conn)

    st.markdown('<div style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:12px">Veri Durumu</div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="display:grid;grid-template-columns:150px 120px 120px;gap:16px;
                padding:10px 16px;border-bottom:1px solid #1e1e2e;
                font-size:10px;color:#666680;letter-spacing:0.1em;text-transform:uppercase">
        <span>Hisse</span><span>Son Veri</span><span>Kayit Sayisi</span>
    </div>
    """, unsafe_allow_html=True)

    for _, row in son_veri.iterrows():
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:150px 120px 120px;gap:16px;
                    padding:12px 16px;border-bottom:1px solid #111120">
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#ffffff">{row['hisse_kodu']}</span>
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#10b981">{str(row['son_tarih'])}</span>
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#666680">{int(row['kayit_sayisi'])}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Feature cache durumu
    feature_durum = pd.read_sql("""
        SELECT hisse_kodu, MAX(tarih) as son_tarih, COUNT(*) as kayit_sayisi
        FROM feature_cache
        GROUP BY hisse_kodu ORDER BY hisse_kodu
    """, conn)

    st.markdown('<div style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:0.15em;text-transform:uppercase;margin:24px 0 12px">Feature Cache Durumu</div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="display:grid;grid-template-columns:150px 120px 120px;gap:16px;
                padding:10px 16px;border-bottom:1px solid #1e1e2e;
                font-size:10px;color:#666680;letter-spacing:0.1em;text-transform:uppercase">
        <span>Hisse</span><span>Son Tarih</span><span>Kayit Sayisi</span>
    </div>
    """, unsafe_allow_html=True)

    for _, row in feature_durum.iterrows():
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:150px 120px 120px;gap:16px;
                    padding:12px 16px;border-bottom:1px solid #111120">
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#ffffff">{row['hisse_kodu']}</span>
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#10b981">{str(row['son_tarih'])}</span>
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#666680">{int(row['kayit_sayisi'])}</span>
        </div>
        """, unsafe_allow_html=True)