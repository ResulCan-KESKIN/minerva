# MINERVA.BIST — Proje Yapısı Özeti

## Genel Mimari

| Katman | Teknoloji |
|--------|-----------|
| UI | Streamlit (Python) |
| Veritabanı | PostgreSQL — Supabase (psycopg2) |
| Anomali Yöntemi | ECDF %95 eşiği (kayan pencere) + t-dağılımı |
| Z-Score Kaynağı | `volume_analysis` tablosu (Supabase trigger ile güncellenir) |
| Otomasyon | GitHub Actions — hafta içi 17:00 UTC (20:00 TR) |
| Tema | Koyu (#0a0a0f), IBM Plex Mono |

---

## Dosya Yapısı

```
minerva_anomali/
├── app.py                    # Streamlit giriş noktası, navigasyon
├── db.py                     # DB bağlantısı (@st.cache_resource)
├── anomali_tespit_ext.py     # Günlük anomali tespiti (paralel, incremental)
├── pages/
│   ├── genel_bakis.py        # Tüm hisse özet
│   ├── hisse_detay.py        # Tek hisse detay + grafik + Z-Score
│   ├── degerlendirme.py      # Anomali onay/ret arayüzü
│   ├── ecdf.py               # ECDF dağılım grafiği
│   ├── backtest.py           # Tarih aralığında geriye dönük tarama
│   └── sistem.py             # Sistem ve veri durumu
├── components/
│   ├── grafik.py             # Candlestick grafik bileşeni
│   ├── anomali_tablo.py      # Anomali tablosu bileşeni
│   └── zscore_panel.py       # Z-Score metrik kartları + grafik
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

### `stock_prices`
| Sütun | Tip | Açıklama |
|-------|-----|----------|
| stock_id | int | FK → stocks.id |
| price_date | date | İşlem günü |
| open_price | float | Açılış fiyatı |
| high_price | float | Gün yükseği |
| low_price | float | Gün düşüğü |
| close_price | float | Kapanış fiyatı |
| volume | float | İşlem hacmi |

### `volume_analysis`
| Sütun | Tip | Açıklama |
|-------|-----|----------|
| stock_id | int | FK → stocks.id |
| price_date | date | İşlem günü |
| z_score_60 | float | Klasik Z-Score (60g pencere) |
| z_score_120 | float | Klasik Z-Score (120g pencere) |
| z_score_robust_60 | float | Robust Z-Score — MAD (60g) |
| z_score_robust_120 | float | Robust Z-Score — MAD (120g) |

> `volume_analysis` Supabase trigger ile günlük otomatik güncellenir.

### `anomali_kayitlari`
| Sütun | Tip | Açıklama |
|-------|-----|----------|
| id | int | PK |
| hisse_kodu | text | THYAO, GARAN, ... |
| anomali_tipi | text | anomali_z60 / anomali_z120 / anomali_rz60 / anomali_rz120 / anomali_t |
| skor | float | Anomali skoru |
| baslangic_zaman | timestamp | Anomali tarihi |
| durum | text | beklemede / onaylandi / ret |
| kaynak | text | volume_analysis / t_dagilimi |

---

## Anomali Tespit Mantığı

### Veri yeterliliğine göre yöntem seçimi

| Veri | Yöntem | Seriler |
|------|--------|---------|
| ≥ 120 gün | ECDF kayan pencere | z_score_60, z_score_120, z_score_robust_60, z_score_robust_120 |
| 60–119 gün | ECDF kayan pencere | z_score_60, z_score_robust_60 |
| < 60 gün | t-dağılımı (`stock_prices.close_price`) | log getiri |

### ECDF eşiği (kayan pencere)
- 60g seriler → son 60 günün z-score dağılımından `quantile(0.95)`
- 120g seriler → son 120 günün z-score dağılımından `quantile(0.95)`

### Incremental çalışma (hisse seviyesi)
- `anomali_kayitlari`'nda zaten kaydı olan hisseler tamamen atlanır (`islenmis_hisseler()`)
- İlk çalışmada tüm geçmiş taranır
- Tekrar çalışmada yalnızca işlenmemiş hisseler işlenir
- `ON CONFLICT DO NOTHING` ile çift kayıt önlenir

### Paralel işlem
- `ThreadPoolExecutor(max_workers=4)` ile 4 hisse eş zamanlı taranır
- Her worker kendi bağlantısını açar/kapatır (`get_conn()` per-worker)
- Toplu yazma `executemany` ile yapılır (`_kaydet_toplu`)

---

## Günlük Pipeline

```
GitHub Actions (17:00 UTC / 20:00 TR)
│
└── python anomali_tespit_ext.py
    ├── Supabase trigger volume_analysis'i zaten güncelledi
    ├── islenmis_hisseler() → işlenmiş hisseleri atla
    └── ThreadPoolExecutor (4 worker)
        ├── Her hisse: zscore_verisi_cek → ECDF / t-dağılımı eşiği
        └── _kaydet_toplu → anomali_kayitlari (ON CONFLICT DO NOTHING)
```

---

## Anomali Tipleri ve Renk Kodları

| Tip | Renk | Açıklama |
|-----|------|----------|
| `anomali_z60` | `#3b82f6` mavi | Klasik Z-Score 60g eşiği aşımı |
| `anomali_z120` | `#06b6d4` camgöbeği | Klasik Z-Score 120g eşiği aşımı |
| `anomali_rz60` | `#f59e0b` sarı | Robust Z-Score (MAD) 60g eşiği aşımı |
| `anomali_rz120` | `#10b981` yeşil | Robust Z-Score (MAD) 120g eşiği aşımı |
| `anomali_t` | `#a78bfa` mor | t-dağılımı ile tespit (az veri) |

---

## Sayfalar

| Sayfa | Açıklama |
|-------|----------|
| Genel Bakış | Tüm hisseler anomali özeti |
| Hisse Detay | Fiyat grafiği + Z-Score paneli + anomali tablosu |
| Değerlendirme | Bekleyen anomalileri onayla / reddet |
| ECDF | 4 serinin empirik dağılım grafiği + istatistik kartları |
| Backtest | Tarih aralığı seç → kayan ECDF ile tüm hisseleri tara |
| Sistem | stock_prices / volume_analysis veri durumu + anomali istatistikleri |

---

## Çalıştırma

```bash
# .env dosyasını doldur
streamlit run app.py
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
