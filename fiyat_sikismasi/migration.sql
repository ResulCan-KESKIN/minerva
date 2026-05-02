-- Fiyat Sıkışması Kayıtları tablosu
-- Supabase SQL Editor'de çalıştır

CREATE TABLE IF NOT EXISTS fiyat_sikismasi_kayitlari (
    id                  SERIAL PRIMARY KEY,
    stock_id            INT REFERENCES stocks(id),
    symbol              TEXT NOT NULL,
    radar               TEXT NOT NULL CHECK (radar IN ('radar1', 'radar2')),
    kutu_baslangic      DATE NOT NULL,
    kutu_bitis          DATE NOT NULL,
    cekirdek_zirve      NUMERIC,
    cekirdek_dip        NUMERIC,
    pencere_uzunlugu    INT,
    fiziki_limit        NUMERIC,
    efor_rasyosu        NUMERIC,
    sok_sayisi          INT,
    sok_hacim_yuzdesi   NUMERIC,
    olusturma_zaman     TIMESTAMP DEFAULT NOW(),
    UNIQUE (stock_id, radar, kutu_baslangic, kutu_bitis)
);

-- stocks tablosuna dolaşım lot sütunu
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS dolasim_lot NUMERIC;

CREATE INDEX IF NOT EXISTS idx_fsk_symbol ON fiyat_sikismasi_kayitlari (symbol);
CREATE INDEX IF NOT EXISTS idx_fsk_kutu_bitis ON fiyat_sikismasi_kayitlari (kutu_bitis DESC);
