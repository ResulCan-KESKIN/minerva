# pages/backtest.py — Tarih aralığında geriye dönük anomali tarama
import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
import os
from datetime import date, timedelta


@st.cache_resource
def get_ext_conn():
    return psycopg2.connect(
        host=os.environ.get("EXT_DB_HOST", "aws-0-eu-west-1.pooler.supabase.com"),
        port=int(os.environ.get("EXT_DB_PORT", 6543)),
        database=os.environ.get("EXT_DB_NAME", "postgres"),
        user=os.environ.get("EXT_DB_USER", "postgres.ewetkqwkjbmblutbejsh"),
        password=os.environ.get("EXT_DB_PASSWORD", "QuantShine2025.")
    )


SERILER = [
    ("z_log_60",   60,  "#3b82f6"),
    ("z_log_120",  120, "#06b6d4"),
    ("rz_log_60",  60,  "#f59e0b"),
    ("rz_log_120", 120, "#10b981"),
]


def hisse_tara(df: pd.DataFrame, baslangic: date, bitis: date) -> dict:
    """
    Her seri için kayan pencere ECDF eşiği hesapla.
    Eşik = o günden önceki pencere kadar günün quantile(0.95).
    Sadece [baslangic, bitis] aralığındaki günleri raporla.
    """
    df = df.copy()
    df["price_date"] = pd.to_datetime(df["price_date"])
    df = df.sort_values("price_date").reset_index(drop=True)

    anomali_sayisi = 0
    max_skor = 0.0
    anomali_gunler = []

    for kolon, pencere, _ in SERILER:
        if kolon not in df.columns:
            continue

        abs_seri = pd.to_numeric(df[kolon], errors="coerce").abs()
        # Kayan eşik: o günden önceki `pencere` günün quantile(0.95)
        esik = abs_seri.shift(1).rolling(pencere, min_periods=pencere // 2).quantile(0.95)

        mask_aralik = (df["price_date"].dt.date >= baslangic) & (df["price_date"].dt.date <= bitis)
        mask_anomali = abs_seri >= esik

        gunler = df[mask_aralik & mask_anomali][["price_date", kolon]].copy()
        gunler["seri"] = kolon
        gunler["skor"] = pd.to_numeric(gunler[kolon], errors="coerce").abs()
        anomali_gunler.append(gunler[["price_date", "seri", "skor"]])

        anomali_sayisi += int((mask_aralik & mask_anomali).sum())
        if not gunler.empty:
            max_skor = max(max_skor, gunler["skor"].max())

    return {
        "anomali_sayisi": int(anomali_sayisi),
        "max_skor": round(max_skor, 4),
        "detay": pd.concat(anomali_gunler) if anomali_gunler else pd.DataFrame(),
    }


def goster():
    st.markdown("""
    <div style="font-family:IBM Plex Mono;font-size:14px;font-weight:500;
                color:#ffffff;letter-spacing:0.06em;margin-bottom:4px">
        BACKTEST — GERİYE DÖNÜK ANOMALİ TARAMA
    </div>
    <div style="font-family:IBM Plex Mono;font-size:11px;color:#666680;
                margin-bottom:24px">
        Seçilen tarih aralığında kayan ECDF eşiğiyle anomali tespiti
    </div>
    """, unsafe_allow_html=True)

    ext_conn = get_ext_conn()

    # ── Tarih aralığı ──
    col1, col2, col3 = st.columns([2, 2, 4])
    with col1:
        baslangic = st.date_input("Başlangıç", value=date.today() - timedelta(days=90), key="bt_bas")
    with col2:
        bitis = st.date_input("Bitiş", value=date.today(), key="bt_bit")

    if baslangic >= bitis:
        st.error("Başlangıç tarihi bitiş tarihinden önce olmalı.")
        return

    tara = st.button("TARA", type="primary")
    if not tara:
        return

    # ── Hisse listesi ──
    hisseler_df = pd.read_sql("""
        SELECT DISTINCT s.id, s.symbol
        FROM stocks s
        INNER JOIN minerva_signals ms ON ms.stock_id = s.id
        WHERE s.is_active = true
        ORDER BY s.symbol
    """, ext_conn)

    if hisseler_df.empty:
        st.warning("Aktif hisse bulunamadı.")
        return

    st.markdown(f"""
    <div style="font-family:IBM Plex Mono;font-size:11px;color:#444460;margin-bottom:16px">
        {len(hisseler_df)} hisse taranıyor...
    </div>
    """, unsafe_allow_html=True)

    ilerleme = st.progress(0)
    sonuclar = []

    for i, (stock_id, symbol) in enumerate(hisseler_df.itertuples(index=False)):
        df = pd.read_sql("""
            SELECT price_date, z_log_60, z_log_120, rz_log_60, rz_log_120
            FROM minerva_signals
            WHERE stock_id = %s
            ORDER BY price_date
        """, ext_conn, params=(int(stock_id),))

        if len(df) < 30:
            ilerleme.progress((i + 1) / len(hisseler_df))
            continue

        sonuc = hisse_tara(df, baslangic, bitis)
        if sonuc["anomali_sayisi"] > 0:
            sonuclar.append({
                "Hisse":         symbol,
                "Anomali Sayısı": sonuc["anomali_sayisi"],
                "Max Skor":       sonuc["max_skor"],
                "_detay":         sonuc["detay"],
                "_symbol":        symbol,
            })

        ilerleme.progress((i + 1) / len(hisseler_df))

    ilerleme.empty()

    if not sonuclar:
        st.markdown("""
        <div style="font-family:IBM Plex Mono;font-size:12px;color:#444460;
                    padding:24px;border:1px solid #1e1e2e;border-radius:2px;text-align:center">
            Seçilen tarih aralığında anomali tespit edilmedi.
        </div>
        """, unsafe_allow_html=True)
        return

    sonuclar.sort(key=lambda x: (-x["Anomali Sayısı"], -x["Max Skor"]))

    # ── Özet ──
    st.markdown(f"""
    <div style="font-family:IBM Plex Mono;font-size:11px;color:#444460;
                letter-spacing:0.08em;margin:20px 0 12px 0;
                border-top:1px solid #1e1e2e;padding-top:16px">
        SONUÇLAR — {len(sonuclar)} hisse · {baslangic} → {bitis}
    </div>
    """, unsafe_allow_html=True)

    # ── Tablo ──
    ozet_df = pd.DataFrame([
        {"#": i + 1, "Hisse": s["Hisse"], "Anomali": s["Anomali Sayısı"], "Max Skor": s["Max Skor"]}
        for i, s in enumerate(sonuclar)
    ])
    st.dataframe(ozet_df, use_container_width=True, hide_index=True)

    # ── Detay expander ──
    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
    for s in sonuclar:
        with st.expander(f"{s['_symbol']} — {s['Anomali Sayısı']} anomali"):
            detay = s["_detay"].copy()
            if detay.empty:
                st.write("Detay yok.")
                continue
            detay["price_date"] = pd.to_datetime(detay["price_date"]).dt.strftime("%d.%m.%Y")
            detay = detay.sort_values("price_date", ascending=False).reset_index(drop=True)
            detay.columns = ["Tarih", "Seri", "Skor"]
            st.dataframe(detay, use_container_width=True, hide_index=True)
