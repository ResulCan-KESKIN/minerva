import psycopg2
import pandas as pd
from sklearn.ensemble import IsolationForest
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

def anomali_tara(hisse_kodu):
    # Hissenin tüm verisini çek
    df = pd.read_sql(f"""
        SELECT zaman, acilis, kapanis, yuksek, dusuk, hacim
        FROM hisse_fiyatlari
        WHERE hisse_kodu = '{hisse_kodu}'
        ORDER BY zaman
    """, conn)

    if len(df) < 5:
        print(f"{hisse_kodu}: Yeterli veri yok, atlanıyor.")
        return

    # Feature'lar: fiyat değişimi, hacim, yüksek-düşük farkı
    df["fiyat_degisimi"] = df["kapanis"] - df["acilis"]
    df["aralik"] = df["yuksek"] - df["dusuk"]
    df["hacim"] = df["hacim"].fillna(0)

    X = df[["fiyat_degisimi", "aralik", "hacim"]]

    # Isolation Forest modeli
    model = IsolationForest(
        contamination=0.05,   # Verinin %20'si anomali olabilir
        random_state=42
    )
    df["tahmin"] = model.fit_predict(X)
    df["skor"] = model.score_samples(X)

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
