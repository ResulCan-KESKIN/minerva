# pages/hisse_detay.py
import streamlit as st
import pandas as pd
from db import get_conn
from components.grafik import candlestick_goster
from components.anomali_tablo import anomali_tablo_goster
from components.zscore_panel import zscore_panel_goster

def goster(secilen):
    conn = get_conn()

    # stock_id bul
    id_df = pd.read_sql(
        "SELECT id FROM stocks WHERE symbol = %s",
        conn, params=(secilen,)
    )
    if id_df.empty:
        st.warning(f"{secilen} bulunamadı.")
        return
    stock_id = int(id_df["id"].iloc[0])

    tab1, tab2, tab3 = st.tabs(["Fiyat Grafigi", "Anomali Kayitlari", "Z-Score Analizi"])

    with tab1:
        df = pd.read_sql("""
            SELECT
                price_date AS zaman,
                open_price  AS acilis,
                high_price  AS yuksek,
                low_price   AS dusuk,
                close_price AS kapanis,
                volume      AS hacim
            FROM stock_prices
            WHERE stock_id = %s
            ORDER BY price_date
        """, conn, params=(stock_id,))

        anomaliler = pd.read_sql("""
            SELECT baslangic_zaman, skor, durum
            FROM anomali_kayitlari
            WHERE hisse_kodu = %s
        """, conn, params=(secilen,))

        if not df.empty:
            candlestick_goster(df, anomaliler, key=f"chart_{secilen}", yukseklik=450)
        else:
            st.info("Fiyat verisi bulunamadi.")

    with tab2:
        anomaliler = pd.read_sql("""
            SELECT id, baslangic_zaman, anomali_tipi,
                   ROUND(skor::numeric, 4) as skor, durum
            FROM anomali_kayitlari
            WHERE hisse_kodu = %s
            ORDER BY skor ASC
        """, conn, params=(secilen,))

        if anomaliler.empty:
            st.info("Anomali kaydi bulunamadi.")
        else:
            anomali_tablo_goster(anomaliler)

    with tab3:
        zscore_df = pd.read_sql("""
            SELECT
                price_date AS tarih,
                z_score_60,
                z_score_120,
                z_score_robust_60,
                z_score_robust_120
            FROM volume_analysis
            WHERE stock_id = %s
            ORDER BY price_date DESC
            LIMIT 120
        """, conn, params=(stock_id,))

        if zscore_df.empty:
            st.info("Z-Score verisi bulunamadi.")
        else:
            zscore_df["tarih"] = pd.to_datetime(zscore_df["tarih"])
            zscore_df = zscore_df.sort_values("tarih")
            zscore_panel_goster(zscore_df)
