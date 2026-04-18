import psycopg2

# Yerel DB
yerel = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    database="minerva",
    user="postgres",
    password="110537"
)

# Supabase
bulut = psycopg2.connect(
    host="aws-1-eu-west-2.pooler.supabase.com",
    port=5432,
    database="postgres",
    user="postgres.wjkpgzbxwxakmnfaqclh",
    password="110537resul.K"
)

yerel_cur = yerel.cursor()
bulut_cur = bulut.cursor()

# Hisse fiyatlarını taşı
print("Hisse fiyatları taşınıyor...")
yerel_cur.execute("SELECT zaman, hisse_kodu, acilis, kapanis, yuksek, dusuk, hacim FROM hisse_fiyatlari")
satirlar = yerel_cur.fetchall()

for satir in satirlar:
    bulut_cur.execute("""
        INSERT INTO hisse_fiyatlari (zaman, hisse_kodu, acilis, kapanis, yuksek, dusuk, hacim)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, satir)

bulut.commit()
print(f"{len(satirlar)} hisse fiyatı taşındı.")

# Anomali kayıtlarını taşı
print("Anomali kayıtları taşınıyor...")
yerel_cur.execute("SELECT hisse_kodu, anomali_tipi, skor, baslangic_zaman, durum, notlar FROM anomali_kayitlari")
anomaliler = yerel_cur.fetchall()

for satir in anomaliler:
    bulut_cur.execute("""
        INSERT INTO anomali_kayitlari (hisse_kodu, anomali_tipi, skor, baslangic_zaman, durum, notlar)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, satir)

bulut.commit()
print(f"{len(anomaliler)} anomali kaydı taşındı.")

print("Taşıma tamamlandı!")
yerel_cur.close()
bulut_cur.close()
yerel.close()
bulut.close()