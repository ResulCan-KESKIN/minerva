# temizlik.py
import psycopg2
import os

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "database": os.environ.get("DB_NAME", "minerva"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "110537")
}

YENI_HISSELER = {
    "TEHOL.IS", "DERHL.IS", "CRDFA.IS", "ADESE.IS", "DSTKF.IS",
    "VSNMD.IS", "HEDEF.IS", "EMKEL.IS", "ALCTL.IS", "SASA.IS",
    "ASELS.IS", "GZNMI.IS", "BORLS.IS", "SUNTK.IS", "SEGYO.IS"
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Mevcut hisseleri çek
cur.execute("""
    SELECT DISTINCT hisse_kodu FROM hisse_fiyatlari
    UNION
    SELECT DISTINCT hisse_kodu FROM feature_cache
    UNION
    SELECT DISTINCT hisse_kodu FROM anomali_kayitlari
""")
mevcut = {r[0] for r in cur.fetchall()}

silinecekler = mevcut - YENI_HISSELER

if not silinecekler:
    print("Silinecek eski hisse yok.")
else:
    print(f"Silinecek hisseler: {silinecekler}")
    for tablo in ["anomali_kayitlari", "feature_cache", "hisse_fiyatlari"]:
        cur.execute(
            f"DELETE FROM {tablo} WHERE hisse_kodu = ANY(%s)",
            (list(silinecekler),)
        )
        print(f"  {tablo}: {cur.rowcount} satır silindi.")
    conn.commit()
    print("Temizlik tamamlandı.")

cur.close()
conn.close()