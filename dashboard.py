import streamlit as st
import psycopg2
import pandas as pd
import plotly.graph_objects as go
from config import DB_CONFIG

st.set_page_config(page_title="Minerva Dashboard", layout="wide")

@st.cache_resource
def baglanti():
    return psycopg2.connect(**DB_CONFIG)

conn = baglanti()

st.title("🏛️ Minerva — BIST Anomali Tespiti")

sayfa = st.sidebar.radio("Sayfa:", ["📈 Fiyat Grafiği", "🚨 Anomali Kayıtları", "✅ Değerlendirme"])

hisseler = pd.read_sql("SELECT DISTINCT hisse_kodu FROM hisse_fiyatlari ORDER BY hisse_kodu", conn)
secilen = st.sidebar.radio("Hisse seç:", hisseler["hisse_kodu"].tolist())

if sayfa == "📈 Fiyat Grafiği":
    st.subheader(f"📈 {secilen} Fiyat Grafiği")

    df = pd.read_sql(f"""
        SELECT zaman, acilis, kapanis, yuksek, dusuk, hacim
        FROM hisse_fiyatlari
        WHERE hisse_kodu = '{secilen}'
        ORDER BY zaman
    """, conn)

    anomali_zamanlari = pd.read_sql(f"""
        SELECT baslangic_zaman, skor, durum
        FROM anomali_kayitlari
        WHERE hisse_kodu = '{secilen}'
    """, conn)

    if not df.empty:
        fig = go.Figure(data=[go.Candlestick(
            x=df["zaman"],
            open=df["acilis"],
            high=df["yuksek"],
            low=df["dusuk"],
            close=df["kapanis"],
            name="Fiyat"
        )])

        if not anomali_zamanlari.empty:
            onaylandi = anomali_zamanlari[anomali_zamanlari["durum"] == "🔴 onaylandi"]
            beklemede = anomali_zamanlari[anomali_zamanlari["durum"] == "🟡 beklemede"]

            for grup, renk, sembol in [
                (beklemede, "orange", "triangle-down"),
                (onaylandi, "red", "x")
            ]:
                if not grup.empty:
                    eslesen = df[df["zaman"].isin(grup["baslangic_zaman"])]
                    if not eslesen.empty:
                        fig.add_trace(go.Scatter(
                            x=eslesen["zaman"],
                            y=eslesen["yuksek"] * 1.01,
                            mode="markers",
                            marker=dict(color=renk, size=12, symbol=sembol),
                            name="Anomali"
                        ))

        fig.update_layout(height=450, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True, key="ana_grafik")
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
        col2.metric("Beklemede", len(anomaliler[anomaliler["durum"] == "🟡 beklemede"]))
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
                
                # O tarihin etrafındaki fiyat verisini göster
                df_detay = pd.read_sql(f"""
                    SELECT zaman, acilis, kapanis, yuksek, dusuk, hacim
                    FROM hisse_fiyatlari
                    WHERE hisse_kodu = '{secilen}'
                    AND zaman BETWEEN '{satir['baslangic_zaman']}'::timestamptz - interval '10 days'
                               AND '{satir['baslangic_zaman']}'::timestamptz + interval '10 days'
                    ORDER BY zaman
                """, conn)

                if not df_detay.empty:
                    fig2 = go.Figure(data=[go.Candlestick(
                        x=df_detay["zaman"],
                        open=df_detay["acilis"],
                        high=df_detay["yuksek"],
                        low=df_detay["dusuk"],
                        close=df_detay["kapanis"]
                    )])
                    fig2.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig2, use_container_width=True, key=f"grafik_{satir['id']}")

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