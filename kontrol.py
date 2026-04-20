# kontrol.py
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

cur.execute("""
    SELECT hisse_kodu, COUNT(*) as kayit
    FROM hisse_fiyatlari
    GROUP BY hisse_kodu
    ORDER BY hisse_kodu
""")

print("Hisse Kodu         | Kayıt")
print("-" * 30)
for row in cur.fetchall():
    print(f"{row[0]:<18} | {row[1]}")

cur.close()
conn.close()