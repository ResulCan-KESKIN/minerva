# anomali_tespit_ext.py — minerva_signals tablosundan Z-Score anomali tespiti
# Yöntem: ≥120g → ECDF 4 seri | 60-119g → ECDF 60g seriler | <60g → t-dağılımı
import psycopg2
import pandas as pd
import numpy as np
from scipy import stats
import os
import warnings

warnings.filterwarnings('ignore')

EXT_CONFIG = {
    "host": os.environ.get("EXT_DB_HOST", "aws-0-eu-west-1.pooler.supabase.com"),
    "port": int(os.environ.get("EXT_DB_PORT", 6543)),
    "database": os.environ.get("EXT_DB_NAME", "postgres"),
    "user": os.environ.get("EXT_DB_USER", "postgres.ewetkqwkjbmblutbejsh"),
    "password": os.environ.get("EXT_DB_PASSWORD", "QuantShine2025.")
}

conn = psycopg2.connect(**EXT_CONFIG)

# 4 bağımsız Z-Score sinyali
ZSCORE_TANIMLARI = [
    ("z_log_60",  "anomali_z60"),
    ("z_log_120", "anomali_z120"),
    ("rz_log_60", "anomali_rz60"),
    ("rz_log_120","anomali_rz120"),
]


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 1 — VERİ ÇEKME
# ═══════════════════════════════════════════════════════════════

def hisseleri_cek() -> list[tuple[int, str]]:
    """minerva_signals'da verisi olan aktif hisseleri çek."""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT s.id, s.symbol
        FROM stocks s
        INNER JOIN minerva_signals ms ON ms.stock_id = s.id
        WHERE s.is_active = true
        ORDER BY s.symbol
    """)
    hisseler = cur.fetchall()
    cur.close()
    return hisseler


def zscore_verisi_cek(stock_id: int) -> pd.DataFrame:
    """minerva_signals tablosundan log getiri Z-Score'larını çek."""
    df = pd.read_sql("""
        SELECT
            price_date,
            adj_close,
            log_getiri,
            z_log_60,
            z_log_120,
            rz_log_60,
            rz_log_120
        FROM minerva_signals
        WHERE stock_id = %s
        ORDER BY price_date
    """, conn, params=(stock_id,))
    return df


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 2 — FEATURE MÜHENDİSLİĞİ (inaktif — ileriki fazlar için)
# ═══════════════════════════════════════════════════════════════

def robust_zscore(seri: pd.Series, pencere: int) -> pd.Series:
    medyan = seri.rolling(pencere, min_periods=pencere // 2).median()
    mad = seri.rolling(pencere, min_periods=pencere // 2).apply(
        lambda x: np.median(np.abs(x - np.median(x))), raw=True
    )
    return (seri - medyan) / (1.4826 * mad.replace(0, np.nan))


def fiyat_hacim_uyumsuzlugu(df: pd.DataFrame) -> pd.DataFrame:
    """
    İNAKTİF — modele girmiyor, ileriki fazlar için hazır bekliyor.
    Pump    : fiyat değişimi yüksek, hacim düşük → sahte hareket
    Birikim : hacim yüksek, fiyat hareketsiz → gizli birikim
    """
    pass


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 3 — ANOMALİ TESPİTİ
# ═══════════════════════════════════════════════════════════════

def _kaydet(cur, symbol: str, tip: str, skor: float, tarih, kaynak: str):
    cur.execute("""
        SELECT id FROM anomali_kayitlari
        WHERE hisse_kodu = %s AND anomali_tipi = %s AND baslangic_zaman::date = %s
    """, (symbol, tip, tarih))
    if cur.fetchone() is None:
        cur.execute("""
            INSERT INTO anomali_kayitlari
                (hisse_kodu, anomali_tipi, skor, baslangic_zaman, durum, kaynak)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (symbol, tip, float(skor), tarih, "beklemede", kaynak))
        return 1
    return 0


def _ecdf_anomaliler(df: pd.DataFrame, tanimlar: list[tuple[str, str]]) -> list[tuple]:
    """ECDF %95 eşiği ile anomali satırlarını döndür: (tip, skor, tarih, kaynak)"""
    sonuclar = []
    for kolon, tip in tanimlar:
        seri = df[["price_date", kolon]].dropna()
        if len(seri) < 10:
            continue
        esik = seri[kolon].abs().quantile(0.95)
        for _, satir in seri[seri[kolon].abs() >= esik].iterrows():
            sonuclar.append((tip, float(satir[kolon].abs()), satir["price_date"].date(), "minerva_signals"))
    return sonuclar


def _t_dagilimi_anomaliler(df: pd.DataFrame) -> list[tuple]:
    """t-dağılımı ile log_getiri anomalilerini tespit et: (tip, skor, tarih, kaynak)"""
    seri = df[["price_date", "log_getiri"]].dropna()
    if len(seri) < 5:
        return []

    n = len(seri)
    mu = seri["log_getiri"].mean()
    se = seri["log_getiri"].std(ddof=1) / np.sqrt(n)
    if se == 0:
        return []

    # %95 eşiği için iki yönlü t kritik değeri (df = n-1)
    t_kritik = stats.t.ppf(0.95, df=n - 1)

    sonuclar = []
    for _, satir in seri.iterrows():
        t_stat = abs((satir["log_getiri"] - mu) / (seri["log_getiri"].std(ddof=1) or 1))
        if t_stat >= t_kritik:
            sonuclar.append(("anomali_t", float(t_stat), satir["price_date"].date(), "t_dagilimi"))
    return sonuclar


def anomali_tara(stock_id: int, symbol: str):
    df = zscore_verisi_cek(stock_id)
    n = len(df)

    if n == 0:
        print(f"{symbol}: Veri yok, atlanıyor.")
        return

    df["price_date"] = pd.to_datetime(df["price_date"])
    cur = conn.cursor()
    toplam = 0

    if n >= 120:
        # Tam ECDF — 4 seri
        anomaliler = _ecdf_anomaliler(df, ZSCORE_TANIMLARI)
        mod = "ECDF 4 seri"
    elif n >= 60:
        # Kısmi ECDF — yalnızca 60g seriler
        tanimlar_60 = [t for t in ZSCORE_TANIMLARI if "60" in t[0]]
        anomaliler = _ecdf_anomaliler(df, tanimlar_60)
        mod = "ECDF 60g"
    else:
        # t-dağılımı
        anomaliler = _t_dagilimi_anomaliler(df)
        mod = "t-dağılımı"

    for tip, skor, tarih, kaynak in anomaliler:
        toplam += _kaydet(cur, symbol, tip, skor, tarih, kaynak)

    conn.commit()
    cur.close()
    print(f"{symbol} [{mod}]: {toplam} yeni anomali kaydedildi.")


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 4 — ÇALIŞTIR
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Minerva Anomali Tespiti Başladı (≥120g ECDF | 60-119g ECDF-60 | <60g t-dağılımı)...")
    print("=" * 60)

    hisseler = hisseleri_cek()
    print(f"Toplam {len(hisseler)} hisse taranacak.\n")

    for stock_id, symbol in hisseler:
        try:
            anomali_tara(stock_id, symbol)
        except Exception as e:
            print(f"{symbol}: HATA — {e}")

    print("=" * 60)
    print("Tarama tamamlandı.")
    conn.close()
