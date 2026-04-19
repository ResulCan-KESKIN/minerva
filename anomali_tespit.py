import psycopg2
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from datetime import datetime
import os

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "database": os.environ.get("DB_NAME", "minerva"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "110537")
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

HISSELER = [
    "THYAO.IS", "GARAN.IS", "ASELS.IS", "EREGL.IS", "BIMAS.IS",
    "AKBNK.IS", "YKBNK.IS", "KCHOL.IS", "SAHOL.IS", "TUPRS.IS",
    "SISE.IS", "PGSUS.IS", "TAVHL.IS", "TCELL.IS", "FROTO.IS"
]

def istatistiksel_motor(df, pencere=20):
    # Fiyat değişimi ve aralık
    df["fiyat_degisimi"] = df["kapanis"] - df["acilis"]
    df["aralik"] = df["yuksek"] - df["dusuk"]
    df["hacim"] = df["hacim"].fillna(0)

    # Rolling istatistikler (20 mum penceresi)
    for kolon in ["fiyat_degisimi", "aralik", "hacim"]:
        ort = df[kolon].rolling(pencere, min_periods=1).mean()
        std = df[kolon].rolling(pencere, min_periods=1).std().replace(0, np.nan)
        df[f"{kolon}_zscore"] = (df[kolon] - ort) / std

    df[[c for c in df.columns if c.endswith("_zscore")]] = (
        df[[c for c in df.columns if c.endswith("_zscore")]].fillna(0)
    )

    # Z-score'u yüksek olanları ön-filtrele (|z| > 4 → kesin aykırı, modele verme)
    z_cols = [c for c in df.columns if c.endswith("_zscore")]
    df["z_max"] = df[z_cols].abs().max(axis=1)
    df["kesin_anomali"] = df["z_max"] > 4

    # StandardScaler ile ölçekle
    feature_cols = ["fiyat_degisimi", "aralik", "hacim",
                    "fiyat_degisimi_zscore", "aralik_zscore", "hacim_zscore"]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df[feature_cols])

    return df, X_scaled

def anomali_tara(hisse_kodu):
    df = pd.read_sql("""
        SELECT zaman, acilis, kapanis, yuksek, dusuk, hacim
        FROM hisse_fiyatlari
        WHERE hisse_kodu = %s
        ORDER BY zaman
    """, conn, params=(hisse_kodu,))

    if len(df) < 5:
        print(f"{hisse_kodu}: Yeterli veri yok, atlanıyor.")
        return

    # İstatistiksel motor
    df, X_scaled = istatistiksel_motor(df)

    # Isolation Forest — artık ölçeklenmiş + zenginleştirilmiş feature'larla
    model = IsolationForest(
        contamination=0.02,
        random_state=42
    )
    df["tahmin"] = model.fit_predict(X_scaled)
    df["skor"] = model.score_samples(X_scaled)

    # Kesin anomalileri de anomali say (IF -1 demese bile)
    df.loc[df["kesin_anomali"], "tahmin"] = -1

    # -1 = anomali, 1 = normal
    anomaliler = df[df["tahmin"] == -1]

    print(f"{hisse_kodu}: {len(anomaliler)} anomali tespit edildi.")

    for _, satir in anomaliler.iterrows():
        # Daha önce kaydedilmiş mi kontrol et
        cur.execute("""
            SELECT id FROM anomali_kayitlari
            WHERE hisse_kodu = %s AND baslangic_zaman = %s
        """, (hisse_kodu, satir["zaman"]))

        if cur.fetchone() is None:
            cur.execute("""
                INSERT INTO anomali_kayitlari
                    (hisse_kodu, anomali_tipi, skor, baslangic_zaman, durum)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                hisse_kodu,
                "isolation_forest",
                float(satir["skor"]),
                satir["zaman"],
                "beklemede"
            ))

    conn.commit()

if __name__ == "__main__":
    print("Anomali taraması başladı...")
    for hisse in HISSELER:
        anomali_tara(hisse)
    print("Tarama tamamlandı.")
    cur.close()
    conn.close()