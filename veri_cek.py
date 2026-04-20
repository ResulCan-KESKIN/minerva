import psycopg2
import os

# Matriks'e geçince sadece bu satırı değiştir:
# from matriks_adapter import MatriksAdapter as Adapter
from yahoo_adapter import YahooAdapter as Adapter

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
    "TEHOL.IS", "DERHL.IS", "CRDFA.IS", "ADESE.IS", "DSTKF.IS",
    "VSNMD.IS", "HEDEF.IS", "EMKEL.IS", "ALCATEL.IS", "SASA.IS",
    "ASELS.IS", "GZNMI.IS", "BORLS.IS", "SUNTK.IS", "SEGYO.IS"
]

adapter = Adapter()

def veri_cek_ve_kaydet(hisse_kodu):
    df = adapter.gunluk_ohlcv(hisse_kodu, period="1d")

    if df.empty:
        print(f"{hisse_kodu} için veri gelmedi.")
        return

    for _, satir in df.iterrows():
        cur.execute("""
            SELECT 1 FROM hisse_fiyatlari 
            WHERE hisse_kodu = %s AND zaman = %s
        """, (hisse_kodu, satir["zaman"]))

        if cur.fetchone() is None:
            cur.execute("""
                INSERT INTO hisse_fiyatlari 
                    (zaman, hisse_kodu, acilis, kapanis, yuksek, dusuk, hacim)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                satir["zaman"],
                hisse_kodu,
                float(satir["acilis"]),
                float(satir["kapanis"]),
                float(satir["yuksek"]),
                float(satir["dusuk"]),
                int(satir["hacim"])
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