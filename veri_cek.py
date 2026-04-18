import yfinance as yf
import psycopg2
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

def veri_cek_ve_kaydet(hisse_kodu):
    hisse = yf.Ticker(hisse_kodu)
    df = hisse.history(period="1d", interval="1d")
    
    if df.empty:
        print(f"{hisse_kodu} için veri gelmedi.")
        return

    for zaman, satir in df.iterrows():
        cur.execute("""
            SELECT 1 FROM hisse_fiyatlari 
            WHERE hisse_kodu = %s AND zaman = %s
        """, (hisse_kodu, zaman))
        
        if cur.fetchone() is None:
            cur.execute("""
                INSERT INTO hisse_fiyatlari 
                    (zaman, hisse_kodu, acilis, kapanis, yuksek, dusuk, hacim)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
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
    print(f"{hisse_kodu}: veri eklendi.")

if __name__ == "__main__":
    print("Veri çekme başladı...")
    for hisse in HISSELER:
        veri_cek_ve_kaydet(hisse)
    print("Tamamlandı.")
    cur.close()
    conn.close()