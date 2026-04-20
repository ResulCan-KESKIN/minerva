import streamlit as st
import pandas as pd
from db import get_conn
from components.grafik import candlestick_goster
from components.anomali_tablo import anomali_tablo_goster
from components.feature_panel import feature_panel_goster

def goster(secilen):
    conn = get_conn()

    tab1, tab2, tab3 = st.tabs(["Fiyat Grafigi", "Anomali Kayitlari", "Feature Analizi"])

    with tab1:
        df = pd.read_sql("""
            SELECT zaman, acilis, kapanis, yuksek, dusuk, hacim
            FROM hisse_fiyatlari
            WHERE hisse_kodu = %s ORDER BY zaman
        """, conn, params=(secilen,))

        anomaliler = pd.read_sql("""
            SELECT baslangic_zaman, skor, durum
            FROM anomali_kayitlari WHERE hisse_kodu = %s
        """, conn, params=(secilen,))

        if not df.empty:
            candlestick_goster(df, anomaliler, key=f"chart_{secilen}", yukseklik=450)
        else:
            st.info("Veri bulunamadi.")

    with tab2:
        anomaliler = pd.read_sql("""
            SELECT id, baslangic_zaman, anomali_tipi,
                   ROUND(skor::numeric, 4) as skor, durum
            FROM anomali_kayitlari
            WHERE hisse_kodu = %s ORDER BY skor ASC
        """, conn, params=(secilen,))

        if anomaliler.empty:
            st.info("Anomali kaydi bulunamadi.")
        else:
            anomali_tablo_goster(anomaliler)

    with tab3:
        feature_df = pd.read_sql("""
            SELECT tarih, fiyat_degisimi_5g, fiyat_degisimi_20g, fiyat_degisimi_60g,
                   volatilite_5g, volatilite_20g, volatilite_60g,
                   rvol_5g, rvol_20g,
                   fiyat_bant_genisligi_5g, fiyat_bant_genisligi_20g
            FROM feature_cache WHERE hisse_kodu = %s
            ORDER BY tarih DESC LIMIT 60
        """, conn, params=(secilen,))

        if feature_df.empty:
            st.info("Feature verisi bulunamadi.")
        else:
            feature_df["tarih"] = pd.to_datetime(feature_df["tarih"])
            feature_df = feature_df.sort_values("tarih")
            feature_panel_goster(feature_df)