# Minerva BIST — Anomali Tespit Sistemi

BIST'te işlem gören hisseler için istatistiksel anomali tespit ve izleme platformu.

## Ne Yapar?

305 aktif BIST hissesini otomatik olarak tarar. `volume_analysis` tablosundaki Z-Score serilerini **ECDF tabanlı kayan pencere eşiği** ile değerlendirerek istatistiksel olarak anlamlı fiyat hareketlerini tespit eder ve analiste sunar.

## Nasıl Çalışır?

### 1. Veri

`volume_analysis` tablosu Supabase trigger ile günlük güncellenir:

| Seri | Yöntem | Pencere |
|------|--------|---------|
| `z_score_60` | Klasik Z-Score | 60 gün |
| `z_score_120` | Klasik Z-Score | 120 gün |
| `z_score_robust_60` | Robust Z-Score (MAD) | 60 gün |
| `z_score_robust_120` | Robust Z-Score (MAD) | 120 gün |

### 2. Anomali Tespiti

Veri yeterliliğine göre yöntem otomatik seçilir:

| Veri | Yöntem | Seriler |
|------|--------|---------|
| ≥ 120 gün | ECDF kayan pencere | 4 seri |
| 60–119 gün | ECDF kayan pencere | 60g seriler |
| < 60 gün | t-dağılımı | log getiri |

- Daha önce işlenmiş hisseler atlanır (`ON CONFLICT DO NOTHING`)
- 4 paralel worker ile hızlandırılmış tarama (`ThreadPoolExecutor`)

### 3. Otomasyon

GitHub Actions ile her hafta içi 20:00 TR saatinde çalışır.

## Ekranlar

| Sayfa | Açıklama |
|-------|----------|
| **Genel Bakış** | Tüm hisseler için anomali özeti |
| **Hisse Detay** | Fiyat grafiği + Z-Score paneli + anomali listesi |
| **Değerlendirme** | Anomalileri onayla / reddet |
| **ECDF** | Empirik dağılım grafiği ve istatistikler |
| **Backtest** | Geçmiş tarih aralığında kayan ECDF ile anomali tarama |
| **Sistem** | DB veri durumu ve anomali istatistikleri |

## Kurulum

```bash
pip install -r requirements.txt
```

`.env` dosyası oluştur:

```
EXT_DB_HOST=...
EXT_DB_PORT=...
EXT_DB_NAME=...
EXT_DB_USER=...
EXT_DB_PASSWORD=...
```

```bash
streamlit run app.py
```

## Teknolojiler

- **Python** — Streamlit, pandas, numpy, scipy, psycopg2
- **Veritabanı** — PostgreSQL (Supabase)
- **CI/CD** — GitHub Actions

## Lisans

MIT
