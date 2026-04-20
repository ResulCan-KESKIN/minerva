import yfinance as yf
import psycopg2
import pandas as pd
from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Pilot hisse listesi (Tunahan/İbrahim onaylayana kadar geçici)
HISSELER = [
    "TEHOL.IS", "DERHL.IS", "CRDFA.IS", "ADESE.IS", "DSTKF.IS",
    "VSNMD.IS", "HEDEF.IS", "EMKEL.IS", "ALCATEL.IS", "SASA.IS",
    "ASELS.IS", "GZNMI.IS", "BORLS.IS", "SUNTK.IS", "SEGYO.IS"
]

def tarihsel_veri_cek(hisse_kodu):
    print(f"{hisse_kodu} tarihsel veri çekiliyor...")
    
    hisse = yf.Ticker(hisse_kodu)
    # Son 2 yıllık günlük veri
    df = hisse.history(period="2y", interval="1d")
    
    if df.empty:
        print(f"{hisse_kodu}: Veri gelmedi, atlanıyor.")
        return 0

    eklenen = 0
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
            eklenen += 1
    
    conn.commit()
    print(f"{hisse_kodu}: {eklenen} yeni satır eklendi.")
    return eklenen

if __name__ == "__main__":
    print("Tarihsel veri yükleme başladı (2 yıl)...")
    toplam = 0
    for hisse in HISSELER:
        toplam += tarihsel_veri_cek(hisse)
    print(f"\nTamamlandı. Toplam {toplam} satır eklendi.")
    cur.close()
    conn.close()