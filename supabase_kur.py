import psycopg2

# Supabase bağlantı testi
conn = psycopg2.connect(
    host= "aws-1-eu-west-2.pooler.supabase.com",
    port=5432,
    database="postgres",
    user="postgres.wjkpgzbxwxakmnfaqclh",
    password="110537resul.K"  # buraya koy
)
cur = conn.cursor()

# Tabloları oluştur
cur.execute("""
    CREATE TABLE IF NOT EXISTS hisse_fiyatlari (
        zaman        TIMESTAMPTZ NOT NULL,
        hisse_kodu   TEXT NOT NULL,
        acilis        DOUBLE PRECISION,
        kapanis       DOUBLE PRECISION,
        yuksek        DOUBLE PRECISION,
        dusuk         DOUBLE PRECISION,
        hacim         BIGINT
    );
""")

cur.execute("""
    CREATE TABLE IF NOT EXISTS anomali_kayitlari (
        id              SERIAL PRIMARY KEY,
        tespit_zamani   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        hisse_kodu      TEXT NOT NULL,
        anomali_tipi    TEXT,
        skor            DOUBLE PRECISION,
        baslangic_zaman TIMESTAMPTZ,
        bitis_zaman     TIMESTAMPTZ,
        durum           TEXT DEFAULT 'beklemede',
        notlar          TEXT
    );
""")

conn.commit()
print("Tablolar oluşturuldu!")
cur.close()
conn.close()