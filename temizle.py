def temizle():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # ILIKE kullanarak büyük/küçük harf duyarlılığını kaldırıyoruz
        cur.execute("DELETE FROM anomali_kayitlari WHERE durum ILIKE 'beklemede';")
        
        silinen_sayisi = cur.rowcount
        conn.commit()
        print(f"Başarılı: {silinen_sayisi} adet eski anomali kaydı temizlendi.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Hata oluştu: {e}")