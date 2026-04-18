import streamlit as st
import psycopg2
import pandas as pd
from streamlit_lightweight_charts import renderLightweightCharts
import os

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

sayfa = st.sidebar.radio("Sayfa:", ["📈 Fiyat Grafiği", "🚨 Anomali Kayıtları", "✅ Değerlendirme"])

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

    anomaliler = pd.read_sql(f"""
        SELECT baslangic_zaman, skor, durum
        FROM anomali_kayitlari
        WHERE hisse_kodu = '{secilen}'
    """, conn)

    if not df.empty:
        # Zaman damgasını unix timestamp'e çevir
        df["zaman"] = pd.to_datetime(df["zaman"]).dt.tz_localize(None)
        df["time"] = df["zaman"].astype("int64") // 10**9

        # Candlestick verisi
        candle_data = df[["time", "acilis", "yuksek", "dusuk", "kapanis"]].rename(columns={
            "acilis": "open",
            "yuksek": "high",
            "dusuk": "low",
            "kapanis": "close"
        }).to_dict("records")

        # Hacim verisi
        hacim_data = df[["time", "hacim"]].rename(columns={"hacim": "value"}).to_dict("records")

        # Anomali işaretleri
        markers = []
        if not anomaliler.empty:
            anomaliler["baslangic_zaman"] = pd.to_datetime(anomaliler["baslangic_zaman"]).dt.tz_localize(None)
            anomaliler["time"] = anomaliler["baslangic_zaman"].astype("int64") // 10**9
            for _, row in anomaliler.iterrows():
                markers.append({
                    "time": int(row["time"]),
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
            "timeScale": {
                "borderColor": "#485c7b",
                "timeVisible": True
            }
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
                    df_detay["time"] = df_detay["zaman"].astype("int64") // 10**9

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
