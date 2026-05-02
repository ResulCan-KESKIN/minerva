import streamlit as st
import pandas as pd
from db import get_conn
from components.grafik import candlestick_goster


def goster(secilen):
    conn = get_conn()

    st.markdown(
        '<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;margin:20px 0 14px 0">'
        '<span style="color:#2e2e48;margin-right:8px">§ 1</span>Anomali Değerlendirme</div>',
        unsafe_allow_html=True,
    )

    id_df = pd.read_sql(
        "SELECT id FROM stocks WHERE symbol = %s",
        conn, params=(secilen,)
    )
    if id_df.empty:
        st.warning(f"{secilen} bulunamadı.")
        return
    stock_id = int(id_df["id"].iloc[0])

    anomaliler = pd.read_sql("""
        SELECT id, baslangic_zaman, skor, durum, notlar
        FROM anomali_kayitlari
        WHERE hisse_kodu = %s
        ORDER BY baslangic_zaman DESC
    """, conn, params=(secilen,))

    if anomaliler.empty:
        st.info("Degerlendirme bekleyen anomali yok.")
        return

    for _, satir in anomaliler.iterrows():
        tarih = str(satir["baslangic_zaman"])[:10]
        skor = round(satir["skor"], 4)

        with st.expander(f"{tarih}   |   Skor: {skor}   |   {satir['durum']}"):
            df_detay = pd.read_sql("""
                SELECT
                    price_date AS zaman,
                    open_price  AS acilis,
                    high_price  AS yuksek,
                    low_price   AS dusuk,
                    close_price AS kapanis,
                    volume      AS hacim
                FROM stock_prices
                WHERE stock_id = %s
                AND price_date BETWEEN %s::date - interval '15 days'
                               AND %s::date + interval '15 days'
                ORDER BY price_date
            """, conn, params=(stock_id, satir["baslangic_zaman"], satir["baslangic_zaman"]))

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
