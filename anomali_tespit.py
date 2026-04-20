import psycopg2
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import os

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "database": os.environ.get("DB_NAME", "minerva"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "110537")
}

conn = psycopg2.connect(**DB_CONFIG)

HISSELER = [
    "TEHOL.IS", "DERHL.IS", "CRDFA.IS", "ADESE.IS", "DSTKF.IS",
    "VSNMD.IS", "HEDEF.IS", "EMKEL.IS", "ALCATEL.IS", "SASA.IS",
    "ASELS.IS", "GZNMI.IS", "BORLS.IS", "SUNTK.IS", "SEGYO.IS"
]

def anomali_tara(hisse_kodu):
    # Feature cache'den veri çek
    df = pd.read_sql("""
        SELECT 
            f.tarih,
            f.fiyat_degisimi_5g,
            f.fiyat_degisimi_20g,
            f.fiyat_degisimi_60g,
            f.volatilite_5g,
            f.volatilite_20g,
            f.volatilite_60g,
            f.rvol_5g,
            f.rvol_20g,
            f.fiyat_bant_genisligi_5g,
            f.fiyat_bant_genisligi_20g
        FROM feature_cache f
        WHERE f.hisse_kodu = %s
        ORDER BY f.tarih
    """, conn, params=(hisse_kodu,))

    if len(df) < 30:
        print(f"{hisse_kodu}: Yeterli feature verisi yok, atlanıyor.")
        return

    df["tarih"] = pd.to_datetime(df["tarih"])
    df = df.dropna()

    # Z-score ile kesin anomali tespiti
    z_features = ["fiyat_degisimi_5g", "volatilite_5g", "rvol_5g", "fiyat_bant_genisligi_5g"]
    for kolon in z_features:
        ort = df[kolon].rolling(20, min_periods=5).mean()
        std = df[kolon].rolling(20, min_periods=5).std().replace(0, np.nan)
        df[f"{kolon}_z"] = (df[kolon] - ort) / std

    df["z_max"] = df[[f"{k}_z" for k in z_features]].abs().max(axis=1)
    df["kesin_anomali"] = df["z_max"] > 4

    # Feature seti
    feature_kolonlar = [
        "fiyat_degisimi_5g", "fiyat_degisimi_20g", "fiyat_degisimi_60g",
        "volatilite_5g", "volatilite_20g", "volatilite_60g",
        "rvol_5g", "rvol_20g",
        "fiyat_bant_genisligi_5g", "fiyat_bant_genisligi_20g"
    ]

    df = df.dropna(subset=feature_kolonlar)
    if len(df) < 10:
        return

    X = df[feature_kolonlar].copy()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Isolation Forest
    model = IsolationForest(contamination=0.02, random_state=42)
    df["tahmin"] = model.fit_predict(X_scaled)
    df["if_skor"] = model.score_samples(X_scaled)

    # Kesin anomalileri de dahil et
    df.loc[df["kesin_anomali"], "tahmin"] = -1

    anomaliler = df[df["tahmin"] == -1]
    print(f"{hisse_kodu}: {len(anomaliler)} anomali ({df['kesin_anomali'].sum()} kesin z-score)")

    cur = conn.cursor()
    for _, satir in anomaliler.iterrows():
        cur.execute("""
            SELECT id FROM anomali_kayitlari
            WHERE hisse_kodu = %s AND baslangic_zaman::date = %s
        """, (hisse_kodu, satir["tarih"].date()))

        if cur.fetchone() is None:
            tip = "kesin_anomali" if satir["kesin_anomali"] else "isolation_forest"
            cur.execute("""
                INSERT INTO anomali_kayitlari
                    (hisse_kodu, anomali_tipi, skor, baslangic_zaman, durum)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                hisse_kodu,
                tip,
                float(satir["if_skor"]),
                satir["tarih"],
                "beklemede"
            ))
    conn.commit()
    cur.close()

if __name__ == "__main__":
    print("Anomali taraması başladı...")
    for hisse in HISSELER:
        anomali_tara(hisse)
    print("Tarama tamamlandı.")
    conn.close()