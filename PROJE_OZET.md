# MINERVA.BIST — Proje Yapısı Özeti

## Genel Mimari
- **Framework**: Streamlit (Python)
- **Veritabanı**: PostgreSQL (psycopg2, `.streamlit/secrets.toml`)
- **ML**: scikit-learn Isolation Forest + Z-score
- **Veri Kaynağı**: Yahoo Finance (`yfinance`) — Matriks adaptörü hazır ama stub
- **Otomasyon**: GitHub Actions (hafta içi 17:00 UTC = 20:00 TR)
- **Tema**: Koyu (#0a0a0f), IBM Plex fontları, mavi/yeşil/turuncu/kırmızı renk sistemi

## Takip Edilen 15 Hisse
`THYAO, GARAN, ASELS, EREGL, BIMAS, AKBNK, YKBNK, KCHOL, SAHOL, TUPRS, SISE, PGSUS, TAVHL, TCELL, FROTO` (hepsi `.IS` uzantılı, Yahoo Finance formatı)

---

## Uygulama Giriş Noktası

### `app.py`
- Streamlit uygulamasını başlatır, dark tema CSS enjekte eder
- Sol üstte "MINERVA.BIST" başlığı + faz göstergesi
- **Radio navigasyon** → 4 sayfa:
  - `Genel Bakış` → `pages/genel_bakis.py`
  - `Hisse Detay` → `pages/hisse_detay.py`
  - `Değerlendirme` → `pages/degerlendirme.py`
  - `Sistem` → `pages/sistem.py`
- **Hisse selectbox** → seçilen değer (`secilen`) sayfa 2-3'e parametre olarak geçer
- Sidebar CSS ile gizlenir

---

## Sayfalar (`pages/`)

### `pages/genel_bakis.py` — "Genel Bakış"
- Hisse seçimi gerektirmez
- **4 özet kart**: Toplam hisse, toplam anomali, beklemede, onaylanan
- **Hisse bazlı tablo**: Her hisse için → Toplam/Beklemede/Onaylı anomali sayısı, en düşük skor, son anomali tarihi
- Veri: `anomali_kayitlari` tablosu (GROUP BY hisse_kodu)

### `pages/hisse_detay.py` — "Hisse Detay"
- `secilen` parametresi gerektirir (hisse kodu)
- **3 sekme**:
  1. **Fiyat Grafiği** → `components/grafik.py::candlestick_goster()` — mum grafiği + anomali işaretleri
  2. **Anomali Kayıtları** → `components/anomali_tablo.py::anomali_tablo_goster()` — tarih/tip/skor/durum tablosu
  3. **Feature Analizi** → `components/feature_panel.py::feature_panel_goster()` — son 60 günün teknik göstergeleri

### `pages/degerlendirme.py` — "Değerlendirme"
- `secilen` parametresi gerektirir
- Beklemedeki her anomali için:
  - Expander: tarih, skor, durum
  - 15 günlük mum grafiği (anomali tarihini merkeze alır)
  - Not alanı (text_area)
  - **Onayla** → `durum = "🔴 onaylandi"`, **Reddet** → `durum = "🟢 ret"`
  - DB günceller + `st.rerun()`

### `pages/sistem.py` — "Sistem"
- Hisse seçimi gerektirmez
- **Veri Durumu**: `hisse_fiyatlari` tablosundan → her hisse: son veri tarihi, kayıt sayısı
- **Feature Cache Durumu**: `feature_cache` tablosundan → her hisse: son tarih, kayıt sayısı

---

## Bileşenler (`components/`)

### `components/grafik.py`
- Kütüphane: `streamlit-lightweight-charts`
- `hazirla_gunluk(df)` → intraday veriyi günlük OHLC'ye indirger
- `candlestick_goster(df, anomaliler, key, yukseklik)`:
  - Koyu tema mum grafiği (yukarı=yeşil, aşağı=kırmızı)
  - Anomali var ise kırmızı ok marker
  - Özelleştirilebilir yükseklik

### `components/anomali_tablo.py`
- `durum_badge(durum)` → HTML span: onaylandi=kırmızı, ret=yeşil, beklemede=turuncu
- `anomali_tablo_goster(anomaliler)` → grid: Tarih / Tip / Skor / Durum (badge ile)

### `components/feature_panel.py`
- `metrik_kart(label, value, renk)` → HTML kart bileşeni
- `feature_panel_goster(feature_df)`:
  - **RVOL**: 5g/20g kartlar (>2=danger, >1.5=warn) + çizgi grafik
  - **Volatilite**: 5g/20g/60g kartlar + çizgi grafik
  - **Fiyat Değişimi**: 5g/20g/60g kümülatif getiri (±renk)
  - **Fiyat Bant Genişliği**: Çizgi grafik (daralma=squeeze sinyali)

---

## Veri Pipeline Dosyaları

### `db.py`
- `get_conn()` — `@st.cache_resource` ile PostgreSQL bağlantısı
- Kimlik bilgileri: `.streamlit/secrets.toml`

### `veri_cek.py`
- Günlük çalışır (GitHub Actions)
- Adapter pattern: `YahooAdapter` veya `MatriksAdapter`
- 15 hisse için günlük OHLCV çeker → `hisse_fiyatlari` tablosuna INSERT (duplicate skip)

### `feature_motor.py`
- `veri_cek.py`'den sonra çalışır
- Hesaplanan özellikler:
  - `getiri`: günlük pct_change
  - `bant`: (high-low)/close
  - `fiyat_degisimi_5g/20g/60g`: kümülatif getiri
  - `volatilite_5g/20g/60g`: rolling std
  - `fiyat_bant_genisligi_5g/20g`: rolling avg bant
  - `hacim_ort_5g/20g/60g`: rolling avg hacim
  - `rvol_5g/20g`: cari hacim / N-günlük ort
- `feature_cache` tablosuna UPSERT (ON CONFLICT)
- Minimum 60 günlük veri gerekir

### `anomali_tespit.py`
- `feature_motor.py`'den sonra çalışır
- **Z-score**: Herhangi bir özellik 20 günlük rolling mean'den >4 std sapıyorsa
  - Kontrol edilen: price_change_5d, volatility_5d, rvol_5d, price_band_width_5d
- **Isolation Forest**: %2 contamination, StandardScaler + 10 feature sütunu
- `anomali_kayitlari` tablosuna INSERT: hisse_kodu, anomali_tipi, skor, baslangic_zaman, durum="beklemede"

### `tarihsel_veri.py`
- Tek seferlik bootstrap scripti
- Yahoo Finance'dan 2 yıllık geçmiş veri çeker → `hisse_fiyatlari`

### `yahoo_adapter.py`
- `yfinance` sarmalayıcı
- `gunluk_ohlcv()` → DataFrame: zaman/acilis/yuksek/dusuk/kapanis/hacim
- `akd_verisi()`, `takas_verisi()`, `kap_bildirimleri()` → boş DataFrame (stub)

### `matriks_adapter.py`
- Matriks API için hazır iskelet (TODO yorumları)
- Aynı interface, 4 metod: gunluk_ohlcv, akd_verisi, takas_verisi, kap_bildirimleri
- Aktif etmek için: `veri_cek.py`'de import değiştirilir

---

## Veritabanı Şeması

### `hisse_fiyatlari`
| Sütun | Tip | Açıklama |
|-------|-----|----------|
| zaman | timestamp | Tarih/saat |
| hisse_kodu | text | THYAO.IS vs |
| acilis | float | Açılış fiyatı |
| kapanis | float | Kapanış fiyatı |
| yuksek | float | Günün yükseği |
| dusuk | float | Günün düşüğü |
| hacim | float | İşlem hacmi |

### `feature_cache`
| Sütun | Açıklama |
|-------|----------|
| tarih | Tarih (PK parçası) |
| hisse_kodu | Hisse kodu (PK parçası) |
| fiyat_degisimi_5g/20g/60g | Kümülatif getiri |
| volatilite_5g/20g/60g | Rolling standart sapma |
| fiyat_bant_genisligi_5g/20g | Rolling bant ortalaması |
| hacim_ort_5g/20g/60g | Rolling hacim ortalaması |
| rvol_5g/20g | Göreceli hacim |
| guncelleme_zamani | Son güncelleme |

### `anomali_kayitlari`
| Sütun | Açıklama |
|-------|----------|
| id | Otomatik artan PK |
| hisse_kodu | THYAO.IS vs |
| anomali_tipi | "kesin_anomali" veya "isolation_forest" |
| skor | Anomali skoru |
| baslangic_zaman | Anomali tarihi |
| durum | "beklemede" / "🔴 onaylandi" / "🟢 ret" |
| notlar | Analist notu |

---

## Sayfa Navigasyon Akışı

```
app.py
├── [Radio] Genel Bakış  →  genel_bakis.goster()
│                              └── anomali_kayitlari GROUP BY hisse
│
├── [Radio] Hisse Detay  →  hisse_detay.goster(secilen)
│   ├── Sekme 1: grafik.candlestick_goster()  ← hisse_fiyatlari + anomali_kayitlari
│   ├── Sekme 2: anomali_tablo.anomali_tablo_goster()  ← anomali_kayitlari
│   └── Sekme 3: feature_panel.feature_panel_goster()  ← feature_cache
│
├── [Radio] Değerlendirme  →  degerlendirme.goster(secilen)
│   └── Her bekleyen anomali:
│       ├── grafik.candlestick_goster()  ← hisse_fiyatlari
│       ├── st.text_area (not)
│       └── Onayla/Reddet → UPDATE anomali_kayitlari SET durum=...
│
└── [Radio] Sistem  →  sistem.goster()
    ├── hisse_fiyatlari: son tarih + kayıt sayısı
    └── feature_cache: son tarih + kayıt sayısı

[Selectbox] secilen hisse kodu → Hisse Detay ve Değerlendirme sayfalarına parametre
```

---

## GitHub Actions Pipeline

**Dosya**: `.github/workflows/gunluk_calisma.yml`
**Tetikleyici**: Hafta içi 17:00 UTC / manuel dispatch

```
1. veri_cek.py        → Yahoo Finance'dan günlük OHLCV çek
2. anomali_tespit.py  → Z-score + Isolation Forest anomali tespiti
3. feature_motor.py   → Teknik feature hesapla
```

Ortam değişkenleri: `DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD` (GitHub Secrets)

---

## Bağımlılıklar

```
streamlit                    # UI framework
psycopg2-binary              # PostgreSQL bağlantısı
pandas                       # Veri işleme
yfinance                     # Yahoo Finance API
scikit-learn                 # Isolation Forest
streamlit-lightweight-charts # Mum grafikleri
```

---

## Çalıştırma

```bash
# Ana uygulama
streamlit run app.py

# Günlük pipeline (GitHub Actions'da otomatik çalışır)
python veri_cek.py
python anomali_tespit.py
python feature_motor.py

# Tek seferlik tarihsel veri yükleme
python tarihsel_veri.py
```
