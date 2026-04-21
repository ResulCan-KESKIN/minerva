# anomali_tespit_ext.py — minerva_signals tablosundan Z-Score anomali tespiti
# Yöntem: Adj Close + Log Getiri Z-Score dağılımının en uç %5'i
import psycopg2
import pandas as pd
import numpy as np
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

def anomali_tara(stock_id: int, symbol: str):
    df = zscore_verisi_cek(stock_id)

    if len(df) < 120:
        print(f"{symbol}: Yeterli veri yok ({len(df)} gün), atlanıyor.")
        return

    df["price_date"] = pd.to_datetime(df["price_date"])

    cur = conn.cursor()
    toplam = 0

    # Her Z-Score için bağımsız anomali tespiti
    for kolon, tip in ZSCORE_TANIMLARI:
        seri = df[["price_date", kolon]].dropna()

        if len(seri) < 30:
            continue

        # Bu kolonun kendi %95 eşiği (mutlak değer üzerinden)
        esik = seri[kolon].abs().quantile(0.95)

        # Eşiği aşan günler anomali
        anomaliler = seri[seri[kolon].abs() >= esik].copy()
        anomaliler["skor"] = anomaliler[kolon].abs()

        for _, satir in anomaliler.iterrows():
            cur.execute("""
                SELECT id FROM anomali_kayitlari
                WHERE hisse_kodu = %s
                AND anomali_tipi = %s
                AND baslangic_zaman::date = %s
            """, (symbol, tip, satir["price_date"].date()))

            if cur.fetchone() is None:
                cur.execute("""
                    INSERT INTO anomali_kayitlari
                        (hisse_kodu, anomali_tipi, skor, baslangic_zaman, durum, kaynak)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    symbol,
                    tip,
                    float(satir["skor"]),
                    satir["price_date"],
                    "beklemede",
                    "minerva_signals"
                ))
                toplam += 1

    conn.commit()
    cur.close()
    print(f"{symbol}: {toplam} yeni anomali kaydedildi.")


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 4 — ÇALIŞTIR
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Minerva Anomali Tespiti Başladı (minerva_signals → %95 Persantil)...")
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
