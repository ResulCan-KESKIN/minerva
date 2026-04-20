import psycopg2
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta



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

def feature_hesapla(hisse_kodu):
    # Tüm veriyi çek
    df = pd.read_sql("""
        SELECT zaman::date as tarih, acilis, kapanis, yuksek, dusuk, hacim
        FROM hisse_fiyatlari
        WHERE hisse_kodu = %s
        ORDER BY zaman
    """, conn, params=(hisse_kodu,))

    if len(df) < 60:
        print(f"{hisse_kodu}: Yeterli veri yok.")
        return

    df["tarih"] = pd.to_datetime(df["tarih"])

    # Günlük bazda gruplama (birden fazla kayıt varsa)
    df = df.groupby("tarih").agg(
        acilis=("acilis", "first"),
        yuksek=("yuksek", "max"),
        dusuk=("dusuk", "min"),
        kapanis=("kapanis", "last"),
        hacim=("hacim", "sum")
    ).reset_index()

    # Fiyat değişimi (getiri)
    df["getiri"] = df["kapanis"].pct_change()

    # Fiyat bandı genişliği = (yuksek - dusuk) / kapanis
    df["bant"] = (df["yuksek"] - df["dusuk"]) / df["kapanis"]

    pencereler = {"5g": 5, "20g": 20, "60g": 60}

    for ad, gun in pencereler.items():
        # Fiyat değişimi (kümülatif getiri)
        df[f"fiyat_degisimi_{ad}"] = df["kapanis"].pct_change(gun)

        # Volatilite (rolling std)
        df[f"volatilite_{ad}"] = df["getiri"].rolling(gun).std()

        # Fiyat bant genişliği ortalaması
        df[f"fiyat_bant_genisligi_{ad}"] = df["bant"].rolling(gun).mean()

        # Hacim ortalaması
        df[f"hacim_ort_{ad}"] = df["hacim"].rolling(gun).mean()

    # RVOL = bugünkü hacim / N günlük ortalama hacim
    df["rvol_5g"] = df["hacim"] / df["hacim_ort_5g"]
    df["rvol_20g"] = df["hacim"] / df["hacim_ort_20g"]

    # Son satırı al (bugünün feature'ları)
    df = df.dropna()
    if df.empty:
        return

    cur = conn.cursor()

    for _, satir in df.iterrows():
        cur.execute("""
            INSERT INTO feature_cache (
                tarih, hisse_kodu,
                fiyat_degisimi_5g, fiyat_degisimi_20g, fiyat_degisimi_60g,
                volatilite_5g, volatilite_20g, volatilite_60g,
                fiyat_bant_genisligi_5g, fiyat_bant_genisligi_20g,
                hacim_ort_5g, hacim_ort_20g, hacim_ort_60g,
                rvol_5g, rvol_20g
            ) VALUES (
                %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (tarih, hisse_kodu) DO UPDATE SET
                fiyat_degisimi_5g = EXCLUDED.fiyat_degisimi_5g,
                fiyat_degisimi_20g = EXCLUDED.fiyat_degisimi_20g,
                fiyat_degisimi_60g = EXCLUDED.fiyat_degisimi_60g,
                volatilite_5g = EXCLUDED.volatilite_5g,
                volatilite_20g = EXCLUDED.volatilite_20g,
                volatilite_60g = EXCLUDED.volatilite_60g,
                fiyat_bant_genisligi_5g = EXCLUDED.fiyat_bant_genisligi_5g,
                fiyat_bant_genisligi_20g = EXCLUDED.fiyat_bant_genisligi_20g,
                hacim_ort_5g = EXCLUDED.hacim_ort_5g,
                hacim_ort_20g = EXCLUDED.hacim_ort_20g,
                hacim_ort_60g = EXCLUDED.hacim_ort_60g,
                rvol_5g = EXCLUDED.rvol_5g,
                rvol_20g = EXCLUDED.rvol_20g,
                guncelleme_zamani = NOW()
        """, (
            satir["tarih"].date(), hisse_kodu,
            satir.get("fiyat_degisimi_5g"),
            satir.get("fiyat_degisimi_20g"),
            satir.get("fiyat_degisimi_60g"),
            satir.get("volatilite_5g"),
            satir.get("volatilite_20g"),
            satir.get("volatilite_60g"),
            satir.get("fiyat_bant_genisligi_5g"),
            satir.get("fiyat_bant_genisligi_20g"),
            satir.get("hacim_ort_5g"),
            satir.get("hacim_ort_20g"),
            satir.get("hacim_ort_60g"),
            satir.get("rvol_5g"),
            satir.get("rvol_20g"),
        ))

    conn.commit()
    cur.close()
    print(f"{hisse_kodu}: {len(df)} satır feature hesaplandı.")

if __name__ == "__main__":
    print("Feature hesaplama başladı...")
    for hisse in HISSELER:
        feature_hesapla(hisse)
    print("Tamamlandı.")
    conn.close()