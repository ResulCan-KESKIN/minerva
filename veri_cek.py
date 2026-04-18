import yfinance as yf
import psycopg2
from datetime import datetime
import time

# Veritabanı bağlantısı
conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    database="minerva",
    user="postgres",
    password="110537"
)
cur = conn.cursor()

# Takip edilecek pilot hisseler
HISSELER = ["THYAO.IS", "GARAN.IS", "ASELS.IS", "EREGL.IS", "BIMAS.IS"]

def veri_cek_ve_kaydet(hisse_kodu):
    hisse = yf.Ticker(hisse_kodu)
    df = hisse.history(period="1d", interval="1h")
    
    if df.empty:
        print(f"{hisse_kodu} için veri gelmedi.")
        return

    for zaman, satir in df.iterrows():
        cur.execute("""
            INSERT INTO hisse_fiyatlari 
                (zaman, hisse_kodu, acilis, kapanis, yuksek, dusuk, hacim)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            zaman,
            hisse_kodu,
            float(satir["Open"]),
            float(satir["Close"]),
            float(satir["High"]),
            float(satir["Low"]),
            int(satir["Volume"])
        ))
    
    conn.commit()
    print(f"{hisse_kodu}: {len(df)} satır eklendi.")

if __name__ == "__main__":
    print("Minerva veri çekme servisi başladı...")
    for hisse in HISSELER:
        veri_cek_ve_kaydet(hisse)
    print("Tamamlandı.")
    cur.close()
    conn.close()