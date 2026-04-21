# pages/sistem.py
import streamlit as st
import pandas as pd
from db import get_conn

def goster():
    conn = get_conn()

    st.markdown('<div style="font-size:10px;color:#666680;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:24px;padding-bottom:8px;border-bottom:1px solid #1e1e2e">Sistem Durumu</div>', unsafe_allow_html=True)

    # Fiyat verisi durumu
    st.markdown('<div style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:12px">Fiyat Verisi Durumu</div>', unsafe_allow_html=True)

    son_veri = pd.read_sql("""
        SELECT
            s.symbol AS hisse_kodu,
            MAX(sp.price_date) AS son_tarih,
            COUNT(*) AS kayit_sayisi
        FROM stock_prices sp
        JOIN stocks s ON s.id = sp.stock_id
        WHERE s.is_active = true
        GROUP BY s.symbol
        ORDER BY s.symbol
    """, conn)

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

    # Volume analysis durumu
    st.markdown('<div style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:0.15em;text-transform:uppercase;margin:24px 0 12px">Z-Score (Volume Analysis) Durumu</div>', unsafe_allow_html=True)

    zscore_durum = pd.read_sql("""
        SELECT
            s.symbol AS hisse_kodu,
            MAX(va.price_date) AS son_tarih,
            COUNT(*) AS kayit_sayisi
        FROM volume_analysis va
        JOIN stocks s ON s.id = va.stock_id
        WHERE s.is_active = true
        GROUP BY s.symbol
        ORDER BY s.symbol
    """, conn)

    st.markdown("""
    <div style="display:grid;grid-template-columns:150px 120px 120px;gap:16px;
                padding:10px 16px;border-bottom:1px solid #1e1e2e;
                font-size:10px;color:#666680;letter-spacing:0.1em;text-transform:uppercase">
        <span>Hisse</span><span>Son Tarih</span><span>Kayit Sayisi</span>
    </div>
    """, unsafe_allow_html=True)

    for _, row in zscore_durum.iterrows():
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:150px 120px 120px;gap:16px;
                    padding:12px 16px;border-bottom:1px solid #111120">
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#ffffff">{row['hisse_kodu']}</span>
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#10b981">{str(row['son_tarih'])}</span>
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#666680">{int(row['kayit_sayisi'])}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Anomali özeti
    st.markdown('<div style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:0.15em;text-transform:uppercase;margin:24px 0 12px">Anomali Kayit Ozeti</div>', unsafe_allow_html=True)

    anomali_ozet = pd.read_sql("""
        SELECT
            COUNT(*) as toplam,
            COUNT(*) FILTER (WHERE durum = 'beklemede') as beklemede,
            COUNT(*) FILTER (WHERE durum = '🔴 onaylandi') as onaylandi,
            COUNT(*) FILTER (WHERE durum = '🟢 ret') as reddedildi,
            COUNT(*) FILTER (WHERE anomali_tipi = 'kesin_anomali') as kesin,
            COUNT(*) FILTER (WHERE anomali_tipi = 'soft_anomali') as soft
        FROM anomali_kayitlari
    """, conn)

    r = anomali_ozet.iloc[0]
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    for col, label, val, renk in [
        (c1, "Toplam",      int(r["toplam"]),      "#ffffff"),
        (c2, "Beklemede",   int(r["beklemede"]),   "#f59e0b"),
        (c3, "Onaylandi",   int(r["onaylandi"]),   "#ef4444"),
        (c4, "Reddedildi",  int(r["reddedildi"]),  "#10b981"),
        (c5, "Kesin",       int(r["kesin"]),       "#ef4444"),
        (c6, "Soft",        int(r["soft"]),        "#f59e0b"),
    ]:
        col.markdown(f"""
        <div style="background:#0f0f1a;border:1px solid #1e1e2e;border-radius:4px;
                    padding:12px 16px">
            <div style="font-size:10px;color:#666680;letter-spacing:0.1em;
                        margin-bottom:4px">{label}</div>
            <div style="font-family:IBM Plex Mono;font-size:22px;color:{renk}">{val}</div>
        </div>
        """, unsafe_allow_html=True)
