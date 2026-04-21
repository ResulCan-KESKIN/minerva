# minerva_bootstrap.py — Yahoo Finance Adj Close → minerva_signals
import psycopg2
import pandas as pd
import numpy as np
import yfinance as yf
import time
import os
import warnings

warnings.filterwarnings('ignore')

DB_CONFIG = {
    "host": os.environ.get("EXT_DB_HOST", "aws-0-eu-west-1.pooler.supabase.com"),
    "port": int(os.environ.get("EXT_DB_PORT", 6543)),
    "database": os.environ.get("EXT_DB_NAME", "postgres"),
    "user": os.environ.get("EXT_DB_USER", "postgres.ewetkqwkjbmblutbejsh"),
    "password": os.environ.get("EXT_DB_PASSWORD", "QuantShine2025.")
}

conn = psycopg2.connect(**DB_CONFIG)


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 1 — YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════

def robust_zscore(seri: pd.Series, pencere: int) -> pd.Series:
    medyan = seri.rolling(pencere, min_periods=pencere // 2).median()
    mad = seri.rolling(pencere, min_periods=pencere // 2).apply(
        lambda x: np.median(np.abs(x - np.median(x))), raw=True
    )
    return (seri - medyan) / (1.4826 * mad.replace(0, np.nan))


def klasik_zscore(seri: pd.Series, pencere: int) -> pd.Series:
    ort = seri.rolling(pencere, min_periods=pencere // 2).mean()
    std = seri.rolling(pencere, min_periods=pencere // 2).std()
    return (seri - ort) / std.replace(0, np.nan)


def tablo_olustur():
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS minerva_signals (
            id          SERIAL PRIMARY KEY,
            stock_id    INTEGER REFERENCES stocks(id),
            price_date  DATE,
            adj_close   FLOAT,
            log_getiri  FLOAT,
            z_log_60    FLOAT,
            z_log_120   FLOAT,
            rz_log_60   FLOAT,
            rz_log_120  FLOAT,
            UNIQUE(stock_id, price_date)
        )
    """)
    conn.commit()
    cur.close()
    print("minerva_signals tablosu hazır.")


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 2 — VERİ ÇEKME VE HESAPLAMA
# ═══════════════════════════════════════════════════════════════

def hisseleri_cek() -> list[tuple[int, str]]:
    cur = conn.cursor()
    cur.execute("""
        SELECT id, symbol FROM stocks
        WHERE is_active = true
        ORDER BY symbol
    """)
    hisseler = cur.fetchall()
    cur.close()
    return hisseler


def hisse_isle(stock_id: int, symbol: str) -> int:
    ticker = f"{symbol}.IS"

    try:
        df = yf.download(ticker, period="10y", interval="1d", auto_adjust=True, progress=False)
    except Exception as e:
        print(f"  {symbol}: yfinance hatası — {e}")
        return 0

    if df.empty:
        print(f"  {symbol}: Veri gelmedi.")
        return 0

    # Adj Close — auto_adjust=True ile Close zaten düzeltilmiş gelir
    df = df[["Close"]].copy()
    df.columns = ["adj_close"]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df["price_date"] = df.index.date
    df = df.reset_index(drop=True)
    df = df.dropna(subset=["adj_close"])

    if len(df) < 60:
        print(f"  {symbol}: Yetersiz veri ({len(df)} gün).")
        return 0

    # Log getiri
    df["log_getiri"] = np.log(df["adj_close"] / df["adj_close"].shift(1))

    # Z-Score'lar (log getiri üzerinden)
    df["z_log_60"]  = klasik_zscore(df["log_getiri"], 60)
    df["z_log_120"] = klasik_zscore(df["log_getiri"], 120)
    df["rz_log_60"] = robust_zscore(df["log_getiri"], 60)
    df["rz_log_120"]= robust_zscore(df["log_getiri"], 120)

    df = df.dropna(subset=["log_getiri"])

    # DB'ye yaz
    cur = conn.cursor()
    eklenen = 0

    for _, satir in df.iterrows():
        try:
            cur.execute("""
                INSERT INTO minerva_signals
                    (stock_id, price_date, adj_close, log_getiri,
                     z_log_60, z_log_120, rz_log_60, rz_log_120)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (stock_id, price_date) DO UPDATE SET
                    adj_close   = EXCLUDED.adj_close,
                    log_getiri  = EXCLUDED.log_getiri,
                    z_log_60    = EXCLUDED.z_log_60,
                    z_log_120   = EXCLUDED.z_log_120,
                    rz_log_60   = EXCLUDED.rz_log_60,
                    rz_log_120  = EXCLUDED.rz_log_120
            """, (
                stock_id,
                satir["price_date"],
                float(satir["adj_close"]),
                float(satir["log_getiri"]) if not np.isnan(satir["log_getiri"]) else None,
                float(satir["z_log_60"])   if not np.isnan(satir["z_log_60"])   else None,
                float(satir["z_log_120"])  if not np.isnan(satir["z_log_120"])  else None,
                float(satir["rz_log_60"])  if not np.isnan(satir["rz_log_60"])  else None,
                float(satir["rz_log_120"]) if not np.isnan(satir["rz_log_120"]) else None,
            ))
            eklenen += 1
        except Exception as e:
            print(f"  {symbol} satır hatası: {e}")
            continue

    conn.commit()
    cur.close()
    return eklenen


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 3 — ÇALIŞTIR
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Minerva Bootstrap Başladı — Adj Close + Log Getiri Z-Score")
    print("=" * 60)

    tablo_olustur()

    hisseler = hisseleri_cek()
    print(f"Toplam {len(hisseler)} hisse işlenecek.\n")

    toplam_eklenen = 0
    hatali = []

    for i, (stock_id, symbol) in enumerate(hisseler, 1):
        print(f"[{i}/{len(hisseler)}] {symbol}...", end=" ")
        try:
            eklenen = hisse_isle(stock_id, symbol)
            print(f"{eklenen} satır")
            toplam_eklenen += eklenen
        except Exception as e:
            print(f"HATA — {e}")
            hatali.append(symbol)

        # Rate limit için bekleme (her 10 hissede 2 saniye)
        if i % 10 == 0:
            time.sleep(2)

    print("=" * 60)
    print(f"Tamamlandı. Toplam {toplam_eklenen} satır eklendi.")
    if hatali:
        print(f"Hatalı hisseler ({len(hatali)}): {hatali}")
    conn.close()
