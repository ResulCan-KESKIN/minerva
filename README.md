# Minerva BIST — Anomali Tespit Sistemi

BIST'te işlem gören hisseler için istatistiksel anomali tespit ve izleme platformu.

## Ne Yapar?

305 aktif BIST hissesini her gün otomatik olarak tarar. Log getiri üzerinden hesaplanan Z-Score serilerini **ECDF tabanlı kayan pencere eşiği** ile değerlendirerek istatistiksel olarak anlamlı hareketleri tespit eder ve analiste sunar.

## Nasıl Çalışır?

### 1. Veri
`yfinance` üzerinden günlük fiyat verisi çekilir. Her hisse için log getiri ve 4 ayrı Z-Score serisi hesaplanarak `minerva_signals` tablosuna yazılır.

| Seri | Yöntem | Pencere |
|------|--------|---------|
| `z_log_60` | Klasik Z-Score | 60 gün |
| `z_log_120` | Klasik Z-Score | 120 gün |
| `rz_log_60` | Robust Z-Score (MAD) | 60 gün |
| `rz_log_120` | Robust Z-Score (MAD) | 120 gün |

### 2. Anomali Tespiti

Her serinin kendi geçmiş dağılımından **kayan ECDF eşiği** (%95 persantil) hesaplanır. Veri yeterliliğine göre yöntem otomatik seçilir:

- **≥ 120 gün** → ECDF, 4 seri
- **60–119 gün** → ECDF, 60g seriler
- **< 60 gün** → t-dağılımı

### 3. Otomasyon

GitHub Actions ile her hafta içi 20:00 (TR) saatinde çalışır. Incremental — her gün yalnızca yeni veriler işlenir.

## Ekranlar

| Sayfa | Açıklama |
|-------|----------|
| **Genel Bakış** | Tüm hisseler için anomali özeti |
| **Hisse Detay** | Fiyat grafiği + anomali listesi |
| **Değerlendirme** | Anomalileri onayla / reddet |
| **ECDF** | Empirik dağılım grafiği ve istatistikler |
| **Backtest** | Geçmiş tarih aralığında anomali tarama |
| **Sistem** | Sistem durumu |

## Kurulum

### Gereksinimler

```bash
pip install -r requirements.txt
```

### Ortam Değişkenleri

`.env` dosyası oluştur (örnek: `.env.example`):

```
EXT_DB_HOST=...
EXT_DB_PORT=...
EXT_DB_NAME=...
EXT_DB_USER=...
EXT_DB_PASSWORD=...
```

### Çalıştırma

```bash
streamlit run app.py
```

### İlk Veri Yükleme

```bash
python minerva_bootstrap.py
```

## Teknolojiler

- **Python** — Streamlit, pandas, numpy, scipy, psycopg2
- **Veritabanı** — PostgreSQL (Supabase)
- **Veri** — Yahoo Finance (yfinance)
- **CI/CD** — GitHub Actions

## Lisans

MIT
