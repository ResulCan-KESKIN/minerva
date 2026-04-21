# MINERVA.BIST — Proje Yapısı Özeti

## Genel Mimari

| Katman | Teknoloji |
|--------|-----------|
| UI | Streamlit (Python) |
| Veritabanı | PostgreSQL — Supabase (psycopg2) |
| Anomali Yöntemi | ECDF %95 eşiği (kayan pencere) + t-dağılımı |
| Veri Kaynağı | Yahoo Finance (`yfinance`) |
| Otomasyon | GitHub Actions — hafta içi 17:00 UTC (20:00 TR) |
| Tema | Koyu (#0a0a0f), IBM Plex Mono, mavi/yeşil/turuncu/kırmızı |

---

## Dosya Yapısı

```
minerva_anomali/
├── app.py                    # Streamlit giriş noktası, navigasyon
├── db.py                     # DB bağlantısı (@st.cache_resource)
├── minerva_bootstrap.py      # Tek seferlik — 10 yıllık geçmiş veri yükleme
├── minerva_guncelle.py       # Günlük fiyat + Z-Score güncelleme
├── anomali_tespit_ext.py     # Günlük anomali tespiti (incremental)
├── pages/
│   ├── genel_bakis.py        # Tüm hisse özet
│   ├── hisse_detay.py        # Tek hisse detay + grafik
│   ├── degerlendirme.py      # Anomali onay/ret arayüzü
│   ├── ecdf.py               # ECDF dağılım grafiği
│   ├── backtest.py           # Tarih aralığında geriye dönük tarama
│   └── sistem.py             # Sistem durumu
└── .github/workflows/
    └── gunluk_calisma.yml    # GitHub Actions pipeline
```

---

## Veritabanı Şeması

### `stocks`
| Sütun | Tip | Açıklama |
|-------|-----|----------|
| id | int | PK |
| symbol | text | THYAO, GARAN, ... |
| is_active | bool | Aktif hisse kontrolü |

### `minerva_signals`
| Sütun | Tip | Açıklama |
|-------|-----|----------|
| stock_id | int | FK → stocks.id |
| price_date | date | İşlem günü |
| adj_close | float | Düzeltilmiş kapanış |
| log_getiri | float | ln(P_t / P_{t-1}) |
| z_log_60 | float | Klasik Z-Score (60g pencere) |
| z_log_120 | float | Klasik Z-Score (120g pencere) |
| rz_log_60 | float | Robust Z-Score (60g pencere) |
| rz_log_120 | float | Robust Z-Score (120g pencere) |

### `anomali_kayitlari`
| Sütun | Tip | Açıklama |
|-------|-----|----------|
| id | int | PK |
| hisse_kodu | text | THYAO, GARAN, ... |
| anomali_tipi | text | anomali_z60 / z120 / rz60 / rz120 / anomali_t |
| skor | float | Anomali skoru (abs Z veya t-istatistiği) |
| baslangic_zaman | timestamp | Anomali tarihi |
| durum | text | beklemede / onaylandi / ret |
| kaynak | text | minerva_signals / t_dagilimi |

---

## Anomali Tespit Mantığı

### Veri yeterliliğine göre yöntem seçimi

| Veri | Yöntem | Seriler |
|------|--------|---------|
| ≥ 120 gün | ECDF kayan pencere | z_log_60, z_log_120, rz_log_60, rz_log_120 |
| 60–119 gün | ECDF kayan pencere | z_log_60, rz_log_60 |
| < 60 gün | t-dağılımı | log_getiri |

### ECDF eşiği (kayan pencere)
- `z_log_60` / `rz_log_60` → son 60 günün z-score dağılımından `quantile(0.95)`
- `z_log_120` / `rz_log_120` → son 120 günün z-score dağılımından `quantile(0.95)`
- Z-score'ların kendisi tüm geçmişten hesaplanmıştır (`minerva_signals`)

### Incremental çalışma
- Her çalışmada `anomali_kayitlari`'ndaki son kayıtlı tarih kontrol edilir
- Yalnızca o tarihten sonraki günler işlenir
- İlk çalışmada tüm geçmiş işlenir

---

## Günlük Pipeline

```
GitHub Actions (17:00 UTC / 20:00 TR)
│
├── python minerva_guncelle.py
│   └── yfinance → son 130 günlük adj_close çek
│       → log_getiri + 4 Z-Score hesapla
│       → minerva_signals'a UPSERT (son 5 gün)
│
└── python anomali_tespit_ext.py
    └── minerva_signals'dan Z-Score çek
        → kayan ECDF / t-dağılımı eşiği hesapla
        → yeni anomalileri anomali_kayitlari'na yaz
```

---

## Sayfalar

### Genel Bakış
- Tüm aktif hisseler için anomali sayısı özeti
- Beklemede / onaylanan / reddedilen dağılımı

### Hisse Detay
- Fiyat + anomali grafiği, son anomali listesi

### Değerlendirme
- Beklemedeki anomalileri onayla / reddet
- Analist not alanı

### ECDF
- Seçilen hisse için 4 serinin empirik dağılım grafiği
- İstatistik kartları (μ, σ, min/max, |z|>2, |z|>3 gün sayısı)
- Hisseye ait kayıtlı anomali tablosu

### Backtest
- Tarih aralığı seç → tüm hisseleri tara
- Her gün için o günden önceki kayan pencere ECDF eşiği kullanılır
- Anomali sayısına göre sıralı hisse listesi + detay expander

### Sistem
- DB bağlantı durumu ve son güncelleme bilgileri

---

## Çalıştırma

```bash
# Ortam değişkenlerini yükle (.env)
# Windows: set EXT_DB_HOST=...
# Linux/Mac: export EXT_DB_HOST=...

# Uygulama
streamlit run app.py

# Günlük pipeline (GitHub Actions'da otomatik)
python minerva_guncelle.py
python anomali_tespit_ext.py

# Tek seferlik — ilk veri yükleme
python minerva_bootstrap.py
```

---

## Bağımlılıklar

```
streamlit
psycopg2-binary
pandas
numpy
scipy
plotly
yfinance
scikit-learn
streamlit-lightweight-charts
```
