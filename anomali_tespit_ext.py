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

def hisseleri_cek(conn) -> list[tuple[int, str]]:
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


PENCERE = {"60": 60, "120": 120}


def _ecdf_anomaliler(df_tam: pd.DataFrame, df_yeni: pd.DataFrame, tanimlar: list[tuple[str, str]]) -> list[tuple]:
    sonuclar = []
    for kolon, tip in tanimlar:
        pencere = next((v for k, v in PENCERE.items() if k in kolon), 60)
        pencere_seri = df_tam[kolon].dropna().iloc[-pencere:]
        if len(pencere_seri) < 10:
            continue
        esik = pencere_seri.abs().quantile(0.95)
        yeni_seri = df_yeni[["price_date", kolon]].dropna()
        for _, satir in yeni_seri[yeni_seri[kolon].abs() >= esik].iterrows():
            sonuclar.append((tip, float(satir[kolon].abs()), satir["price_date"].date(), "minerva_signals"))
    return sonuclar


def _t_dagilimi_anomaliler(df_tam: pd.DataFrame, df_yeni: pd.DataFrame) -> list[tuple]:
    tam_seri = df_tam["log_getiri"].dropna()
    if len(tam_seri) < 5:
        return []
    n = len(tam_seri)
    mu = tam_seri.mean()
    std = tam_seri.std(ddof=1) or 1
    t_kritik = stats.t.ppf(0.95, df=n - 1)
    sonuclar = []
    for _, satir in df_yeni[["price_date", "log_getiri"]].dropna().iterrows():
        t_stat = abs((satir["log_getiri"] - mu) / std)
        if t_stat >= t_kritik:
            sonuclar.append(("anomali_t", float(t_stat), satir["price_date"].date(), "t_dagilimi"))
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
        anomaliler = _ecdf_anomaliler(df_tam, df_yeni, ZSCORE_TANIMLARI)
        mod = "ECDF 4 seri"
    elif n >= 60:
        tanimlar_60 = [t for t in ZSCORE_TANIMLARI if "60" in t[0]]
        anomaliler = _ecdf_anomaliler(df_tam, df_yeni, tanimlar_60)
        mod = "ECDF 60g"
    else:
        anomaliler = _t_dagilimi_anomaliler(df_tam, df_yeni)
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
    print("Minerva Anomali Tespiti Başladı (≥120g ECDF | 60-119g ECDF-60 | <60g t-dağılımı)...")
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
