# anomali_tespit_ext.py — volume_analysis tablosundan Z-Score anomali tespiti
# Yöntem: ≥120g → ECDF 4 seri | 60-119g → ECDF 60g | 0-59g → t-dağılımı
import psycopg2
import pandas as pd
import numpy as np
from scipy import stats
import os
import warnings

warnings.filterwarnings('ignore')

EXT_CONFIG = {
    "host": os.environ["EXT_DB_HOST"],
    "port": int(os.environ["EXT_DB_PORT"]),
    "database": os.environ["EXT_DB_NAME"],
    "user": os.environ["EXT_DB_USER"],
    "password": os.environ["EXT_DB_PASSWORD"],
}

# 4 bağımsız Z-Score sinyali
ZSCORE_4 = [
    ("z_score_60",         "anomali_z60"),
    ("z_score_120",        "anomali_z120"),
    ("z_score_robust_60",  "anomali_rz60"),
    ("z_score_robust_120", "anomali_rz120"),
]

# 60g seriler
ZSCORE_60 = [
    ("z_score_60",        "anomali_z60"),
    ("z_score_robust_60", "anomali_rz60"),
]

PENCERE = {"60": 60, "120": 120}


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 1 — VERİ ÇEKME
# ═══════════════════════════════════════════════════════════════

def hisseleri_cek(conn) -> list[tuple[int, str]]:
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT s.id, s.symbol
        FROM stocks s
        INNER JOIN volume_analysis va ON va.stock_id = s.id
        WHERE s.is_active = true
        ORDER BY s.symbol
    """)
    hisseler = cur.fetchall()
    cur.close()
    return hisseler


def son_islenen_tarih(conn, symbol: str):
    cur = conn.cursor()
    cur.execute("""
        SELECT MAX(baslangic_zaman::date)
        FROM anomali_kayitlari
        WHERE hisse_kodu = %s
    """, (symbol,))
    sonuc = cur.fetchone()[0]
    cur.close()
    return sonuc


def zscore_verisi_cek(conn, stock_id: int) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT
            price_date,
            z_score_60,
            z_score_120,
            z_score_robust_60,
            z_score_robust_120
        FROM volume_analysis
        WHERE stock_id = %s
        ORDER BY price_date
    """, conn, params=(stock_id,))


def fiyat_verisi_cek(conn, stock_id: int) -> pd.DataFrame:
    """t-dağılımı için ham fiyat verisi."""
    return pd.read_sql("""
        SELECT price_date, close_price
        FROM stock_prices
        WHERE stock_id = %s
        ORDER BY price_date
    """, conn, params=(stock_id,))


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
    """İNAKTİF — ileriki fazlar için hazır bekliyor."""
    pass


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 3 — ANOMALİ TESPİTİ
# ═══════════════════════════════════════════════════════════════

def _kaydet(cur, symbol: str, tip: str, skor: float, tarih, kaynak: str) -> int:
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


def _ecdf_anomaliler(df_tam: pd.DataFrame, df_yeni: pd.DataFrame, tanimlar: list[tuple]) -> list[tuple]:
    sonuclar = []
    for kolon, tip in tanimlar:
        pencere = next((v for k, v in PENCERE.items() if k in kolon), 60)
        pencere_seri = df_tam[kolon].dropna().iloc[-pencere:]
        if len(pencere_seri) < 5:
            continue

        esik = float(pencere_seri.abs().quantile(0.95))

        yeni_seri = df_yeni[["price_date", kolon]].copy()
        yeni_seri[kolon] = pd.to_numeric(yeni_seri[kolon], errors="coerce")
        yeni_seri = yeni_seri.dropna()

        for _, satir in yeni_seri[yeni_seri[kolon].abs() >= esik].iterrows():
            sonuclar.append((tip, float(abs(satir[kolon])), satir["price_date"].date(), "volume_analysis"))

    return sonuclar


def _t_dagilimi_anomaliler(conn, stock_id: int, df_yeni: pd.DataFrame) -> list[tuple]:
    """Ham fiyat üzerinden log getiri → t-dağılımı ile anomali tespiti."""
    df_fiyat = fiyat_verisi_cek(conn, stock_id)

    if len(df_fiyat) < 3:
        return []

    df_fiyat["price_date"] = pd.to_datetime(df_fiyat["price_date"])
    df_fiyat["close_price"] = pd.to_numeric(df_fiyat["close_price"], errors="coerce")
    df_fiyat = df_fiyat.dropna()
    df_fiyat["log_getiri"] = np.log(df_fiyat["close_price"] / df_fiyat["close_price"].shift(1))
    df_fiyat = df_fiyat.dropna(subset=["log_getiri"])

    if len(df_fiyat) < 3:
        return []

    mu = float(df_fiyat["log_getiri"].mean())
    std = float(df_fiyat["log_getiri"].std(ddof=1)) or 1.0
    n = len(df_fiyat)
    t_kritik = float(stats.t.ppf(0.95, df=n - 1))

    yeni_tarihler = set(pd.to_datetime(df_yeni["price_date"]).dt.date)
    sonuclar = []

    for _, satir in df_fiyat[df_fiyat["price_date"].dt.date.isin(yeni_tarihler)].iterrows():
        t_stat = float(abs((satir["log_getiri"] - mu) / std))
        if t_stat >= t_kritik:
            sonuclar.append(("anomali_t", t_stat, satir["price_date"].date(), "t_dagilimi"))

    return sonuclar


def anomali_tara(conn, stock_id: int, symbol: str):
    df_tam = zscore_verisi_cek(conn, stock_id)
    n = len(df_tam)

    if n == 0:
        print(f"{symbol}: Veri yok, atlanıyor.")
        return

    df_tam["price_date"] = pd.to_datetime(df_tam["price_date"])

    son_tarih = son_islenen_tarih(conn, symbol)
    if son_tarih is not None:
        df_yeni = df_tam[df_tam["price_date"].dt.date > son_tarih].copy()
    else:
        df_yeni = df_tam.copy()

    if df_yeni.empty:
        print(f"{symbol}: Yeni veri yok, atlanıyor.")
        return

    cur = conn.cursor()
    toplam = 0

    if n >= 120:
        anomaliler = _ecdf_anomaliler(df_tam, df_yeni, ZSCORE_4)
        mod = "ECDF 4 seri"
    elif n >= 60:
        anomaliler = _ecdf_anomaliler(df_tam, df_yeni, ZSCORE_60)
        mod = "ECDF 60g"
    else:
        anomaliler = _t_dagilimi_anomaliler(conn, stock_id, df_yeni)
        mod = "t-dağılımı"

    for tip, skor, tarih, kaynak in anomaliler:
        toplam += _kaydet(cur, symbol, tip, skor, tarih, kaynak)

    conn.commit()
    cur.close()
    print(f"{symbol} [{mod}]: {toplam} yeni anomali, {len(df_yeni)} gün tarandı.")


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 4 — ÇALIŞTIR
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Minerva Anomali Tespiti Başladı (≥120g ECDF | 60-119g ECDF-60 | 0-59g t-dağılımı)...")
    print("=" * 60)

    conn = psycopg2.connect(**EXT_CONFIG)
    try:
        hisseler = hisseleri_cek(conn)
        print(f"Toplam {len(hisseler)} hisse taranacak.\n")

        for stock_id, symbol in hisseler:
            try:
                anomali_tara(conn, stock_id, symbol)
            except Exception as e:
                print(f"{symbol}: HATA — {e}")
    finally:
        conn.close()

    print("=" * 60)
    print("Tarama tamamlandı.")
