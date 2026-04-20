import streamlit as st
import psycopg2
import pandas as pd
from streamlit_lightweight_charts import renderLightweightCharts

DB_CONFIG = {
    "host": st.secrets["DB_HOST"],
    "port": int(st.secrets["DB_PORT"]),
    "database": st.secrets["DB_NAME"],
    "user": st.secrets["DB_USER"],
    "password": st.secrets["DB_PASSWORD"]
}

st.set_page_config(page_title="Minerva Dashboard", layout="wide")

@st.cache_resource
def baglanti():
    return psycopg2.connect(**DB_CONFIG)

conn = baglanti()

st.title("🏛️ Minerva — BIST Anomali Tespiti")

sayfa = st.sidebar.radio("Sayfa:", ["📈 Fiyat Grafiği", "🚨 Anomali Kayıtları", "✅ Değerlendirme", "📊 Feature Analizi"])

hisseler = pd.read_sql("SELECT DISTINCT hisse_kodu FROM hisse_fiyatlari ORDER BY hisse_kodu", conn)
secilen = st.sidebar.selectbox("Hisse seç:", hisseler["hisse_kodu"].tolist())

if sayfa == "📈 Fiyat Grafiği":
    st.subheader(f"📈 {secilen} Fiyat Grafiği")

    df = pd.read_sql(f"""
        SELECT zaman, acilis, kapanis, yuksek, dusuk, hacim
        FROM hisse_fiyatlari
        WHERE hisse_kodu = '{secilen}'
        ORDER BY zaman
    """, conn)

    df["zaman"] = pd.to_datetime(df["zaman"]).dt.tz_localize(None)
    df["tarih"] = df["zaman"].dt.date
    df = df.groupby("tarih").agg(
        acilis=("acilis", "first"),
        yuksek=("yuksek", "max"),
        dusuk=("dusuk", "min"),
        kapanis=("kapanis", "last"),
        hacim=("hacim", "sum")
    ).reset_index()
    df["time"] = df["tarih"].astype(str)

    anomaliler = pd.read_sql(f"""
        SELECT baslangic_zaman, skor, durum
        FROM anomali_kayitlari
        WHERE hisse_kodu = '{secilen}'
    """, conn)

    if not df.empty:
        candle_data = df[["time", "acilis", "yuksek", "dusuk", "kapanis"]].rename(columns={
            "acilis": "open", "yuksek": "high", "dusuk": "low", "kapanis": "close"
        }).to_dict("records")

        hacim_data = df[["time", "hacim"]].rename(columns={"hacim": "value"}).to_dict("records")

        markers = []
        if not anomaliler.empty:
            anomaliler["tarih"] = pd.to_datetime(anomaliler["baslangic_zaman"]).dt.tz_localize(None).dt.date.astype(str)
            for _, row in anomaliler.iterrows():
                markers.append({
                    "time": row["tarih"],
                    "position": "aboveBar",
                    "color": "#ff4444",
                    "shape": "arrowDown",
                    "text": "⚠️"
                })

        chart_options = {
            "layout": {
                "background": {"type": "solid", "color": "#0e1117"},
                "textColor": "#ffffff"
            },
            "grid": {
                "vertLines": {"color": "#1e2130"},
                "horzLines": {"color": "#1e2130"}
            },
            "crosshair": {"mode": 1},
            "timeScale": {"borderColor": "#485c7b"}
        }

        series = [
            {
                "type": "Candlestick",
                "data": candle_data,
                "markers": markers,
                "options": {
                    "upColor": "#26a69a",
                    "downColor": "#ef5350",
                    "borderVisible": False,
                    "wickUpColor": "#26a69a",
                    "wickDownColor": "#ef5350"
                }
            },
            {
                "type": "Histogram",
                "data": hacim_data,
                "options": {
                    "color": "#385263",
                    "priceFormat": {"type": "volume"},
                    "priceScaleId": "volume"
                }
            }
        ]

        renderLightweightCharts([{
            "chart": chart_options,
            "series": series
        }], key=f"chart_{secilen}")

    else:
        st.warning("Bu hisse için veri yok.")

elif sayfa == "🚨 Anomali Kayıtları":
    st.subheader(f"🚨 {secilen} Anomali Kayıtları")

    anomaliler = pd.read_sql(f"""
        SELECT id, tespit_zamani, anomali_tipi,
               ROUND(skor::numeric, 4) as skor,
               baslangic_zaman, durum, notlar
        FROM anomali_kayitlari
        WHERE hisse_kodu = '{secilen}'
        ORDER BY tespit_zamani DESC
    """, conn)

    if anomaliler.empty:
        st.info("Bu hisse için anomali kaydı yok.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Toplam", len(anomaliler))
        col2.metric("Beklemede", len(anomaliler[anomaliler["durum"] == "beklemede"]))
        col3.metric("Onaylandı", len(anomaliler[anomaliler["durum"] == "🔴 onaylandi"]))
        st.dataframe(anomaliler, use_container_width=True)

elif sayfa == "✅ Değerlendirme":
    st.subheader(f"✅ {secilen} — Anomali Değerlendirme")
    st.caption("Her anomaliyi incele, gerçek manipülasyon mu değil mi karar ver.")

    anomaliler = pd.read_sql(f"""
        SELECT id, baslangic_zaman, skor, durum, notlar
        FROM anomali_kayitlari
        WHERE hisse_kodu = '{secilen}'
        ORDER BY skor ASC
    """, conn)

    if anomaliler.empty:
        st.info("Değerlendirilecek anomali yok.")
    else:
        for _, satir in anomaliler.iterrows():
            with st.expander(f"📅 {str(satir['baslangic_zaman'])[:10]}  |  Skor: {round(satir['skor'], 4)}  |  {satir['durum']}"):

                df_detay = pd.read_sql(f"""
                    SELECT zaman, acilis, kapanis, yuksek, dusuk
                    FROM hisse_fiyatlari
                    WHERE hisse_kodu = '{secilen}'
                    AND zaman BETWEEN '{satir['baslangic_zaman']}'::timestamptz - interval '10 days'
                               AND '{satir['baslangic_zaman']}'::timestamptz + interval '10 days'
                    ORDER BY zaman
                """, conn)

                if not df_detay.empty:
                    df_detay["zaman"] = pd.to_datetime(df_detay["zaman"]).dt.tz_localize(None)
                    df_detay["tarih"] = df_detay["zaman"].dt.date
                    df_detay = df_detay.groupby("tarih").agg(
                        acilis=("acilis", "first"),
                        yuksek=("yuksek", "max"),
                        dusuk=("dusuk", "min"),
                        kapanis=("kapanis", "last")
                    ).reset_index()
                    df_detay["time"] = df_detay["tarih"].astype(str)

                    detay_data = df_detay[["time", "acilis", "yuksek", "dusuk", "kapanis"]].rename(columns={
                        "acilis": "open", "yuksek": "high", "dusuk": "low", "kapanis": "close"
                    }).to_dict("records")

                    renderLightweightCharts([{
                        "chart": {
                            "layout": {"background": {"type": "solid", "color": "#0e1117"}, "textColor": "#ffffff"},
                            "grid": {"vertLines": {"color": "#1e2130"}, "horzLines": {"color": "#1e2130"}},
                            "height": 200
                        },
                        "series": [{
                            "type": "Candlestick",
                            "data": detay_data,
                            "options": {
                                "upColor": "#26a69a",
                                "downColor": "#ef5350",
                                "borderVisible": False,
                                "wickUpColor": "#26a69a",
                                "wickDownColor": "#ef5350"
                            }
                        }]
                    }], key=f"detay_{satir['id']}")

                not_metni = st.text_area("Not:", value=satir["notlar"] if satir["notlar"] else "", key=f"not_{satir['id']}")

                col1, col2, col3 = st.columns(3)

                if col1.button("🔴 Onayla", key=f"onayla_{satir['id']}"):
                    cur = conn.cursor()
                    cur.execute("UPDATE anomali_kayitlari SET durum='🔴 onaylandi', notlar=%s WHERE id=%s",
                                (not_metni, satir["id"]))
                    conn.commit()
                    cur.close()
                    st.success("Onaylandı!")
                    st.rerun()

                if col2.button("🟢 Reddet", key=f"reddet_{satir['id']}"):
                    cur = conn.cursor()
                    cur.execute("UPDATE anomali_kayitlari SET durum='🟢 ret', notlar=%s WHERE id=%s",
                                (not_metni, satir["id"]))
                    conn.commit()
                    cur.close()
                    st.success("Reddedildi!")
                    st.rerun()

                if col3.button("💾 Not Kaydet", key=f"not_kaydet_{satir['id']}"):
                    cur = conn.cursor()
                    cur.execute("UPDATE anomali_kayitlari SET notlar=%s WHERE id=%s",
                                (not_metni, satir["id"]))
                    conn.commit()
                    cur.close()
                    st.success("Not kaydedildi!")
                    st.rerun()
    
elif sayfa == "📊 Feature Analizi":
    st.subheader(f"📊 {secilen} — Feature Analizi")

    feature_df = pd.read_sql(f"""
        SELECT tarih,
               fiyat_degisimi_5g, fiyat_degisimi_20g, fiyat_degisimi_60g,
               volatilite_5g, volatilite_20g, volatilite_60g,
               rvol_5g, rvol_20g,
               fiyat_bant_genisligi_5g, fiyat_bant_genisligi_20g
        FROM feature_cache
        WHERE hisse_kodu = '{secilen}'
        ORDER BY tarih DESC
        LIMIT 60
    """, conn)

    if feature_df.empty:
        st.info("Bu hisse için feature verisi yok.")
    else:
        feature_df["tarih"] = pd.to_datetime(feature_df["tarih"])
        feature_df = feature_df.sort_values("tarih")

        # RVOL
        st.markdown("#### 📈 Göreceli Hacim (RVOL)")
        st.caption("1.0 = normal hacim. 2.0 = normalin 2 katı hacim.")
        col1, col2 = st.columns(2)
        son = feature_df.iloc[-1]
        col1.metric("RVOL 5G", f"{son['rvol_5g']:.2f}")
        col2.metric("RVOL 20G", f"{son['rvol_20g']:.2f}")
        st.line_chart(feature_df.set_index("tarih")[["rvol_5g", "rvol_20g"]])

        # Volatilite
        st.markdown("#### 🌊 Volatilite")
        st.caption("Günlük fiyat değişiminin standart sapması.")
        col1, col2, col3 = st.columns(3)
        col1.metric("Vol 5G", f"{son['volatilite_5g']:.4f}")
        col2.metric("Vol 20G", f"{son['volatilite_20g']:.4f}")
        col3.metric("Vol 60G", f"{son['volatilite_60g']:.4f}")
        st.line_chart(feature_df.set_index("tarih")[["volatilite_5g", "volatilite_20g", "volatilite_60g"]])

        # Fiyat değişimi
        st.markdown("#### 💹 Kümülatif Fiyat Değişimi")
        st.caption("Seçilen pencerede toplam fiyat değişimi.")
        col1, col2, col3 = st.columns(3)
        col1.metric("5 Günlük", f"{son['fiyat_degisimi_5g']*100:.2f}%")
        col2.metric("20 Günlük", f"{son['fiyat_degisimi_20g']*100:.2f}%")
        col3.metric("60 Günlük", f"{son['fiyat_degisimi_60g']*100:.2f}%")

        # Fiyat bant genişliği
        st.markdown("#### 📏 Fiyat Bant Genişliği")
        st.caption("(Yüksek - Düşük) / Kapanış ortalaması. Daralma = sıkışma sinyali.")
        st.line_chart(feature_df.set_index("tarih")[["fiyat_bant_genisligi_5g", "fiyat_bant_genisligi_20g"]])

        # Ham tablo
        with st.expander("📋 Ham Veri"):
            st.dataframe(feature_df, use_container_width=True)