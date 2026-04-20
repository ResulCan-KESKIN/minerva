import streamlit as st
import pandas as pd
from db import get_conn
from components.grafik import candlestick_goster

def goster(secilen):
    conn = get_conn()

    st.markdown('<div style="font-size:10px;color:#666680;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:24px;padding-bottom:8px;border-bottom:1px solid #1e1e2e">Anomali Degerlendirme</div>', unsafe_allow_html=True)

    anomaliler = pd.read_sql("""
        SELECT id, baslangic_zaman, skor, durum, notlar
        FROM anomali_kayitlari
        WHERE hisse_kodu = %s ORDER BY skor ASC
    """, conn, params=(secilen,))

    if anomaliler.empty:
        st.info("Degerlendirme bekleyen anomali yok.")
        return

    for _, satir in anomaliler.iterrows():
        tarih = str(satir["baslangic_zaman"])[:10]
        skor = round(satir["skor"], 4)

        with st.expander(f"{tarih}   |   Skor: {skor}   |   {satir['durum']}"):
            df_detay = pd.read_sql("""
                SELECT zaman, acilis, kapanis, yuksek, dusuk, hacim
                FROM hisse_fiyatlari
                WHERE hisse_kodu = %s
                AND zaman BETWEEN %s::timestamptz - interval '15 days'
                           AND %s::timestamptz + interval '15 days'
                ORDER BY zaman
            """, conn, params=(secilen, satir["baslangic_zaman"], satir["baslangic_zaman"]))

            if not df_detay.empty:
                candlestick_goster(df_detay, key=f"detay_{satir['id']}", yukseklik=220)

            not_metni = st.text_area(
                "Degerlendirme notu",
                value=satir["notlar"] if satir["notlar"] else "",
                key=f"not_{satir['id']}", height=80
            )

            c1, c2, _ = st.columns([1, 1, 4])
            if c1.button("Onayla", key=f"onayla_{satir['id']}"):
                cur = conn.cursor()
                cur.execute(
                    "UPDATE anomali_kayitlari SET durum='🔴 onaylandi', notlar=%s WHERE id=%s",
                    (not_metni, satir["id"])
                )
                conn.commit(); cur.close()
                st.success("Onaylandi."); st.rerun()

            if c2.button("Reddet", key=f"reddet_{satir['id']}"):
                cur = conn.cursor()
                cur.execute(
                    "UPDATE anomali_kayitlari SET durum='🟢 ret', notlar=%s WHERE id=%s",
                    (not_metni, satir["id"])
                )
                conn.commit(); cur.close()
                st.success("Reddedildi."); st.rerun()