# minerva_guncelle.py — Günlük adj close çekip minerva_signals güncelle
import psycopg2
import pandas as pd
import numpy as np
import yfinance as yf
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


def hisseleri_cek() -> list[tuple[int, str]]:
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


def hisse_guncelle(stock_id: int, symbol: str):
    ticker = f"{symbol}.IS"

    # Son 130 günü çek (Z-Score için yeterli geçmiş)
    try:
        df = yf.download(ticker, period="130d", auto_adjust=True, progress=False)
    except Exception as e:
        print(f"  {symbol}: yfinance hatası — {e}")
        return 0

    if df.empty:
        print(f"  {symbol}: Veri gelmedi.")
        return 0

    df = df[["Close"]].copy()
    df.columns = ["adj_close"]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df["price_date"] = df.index.date
    df = df.reset_index(drop=True).dropna(subset=["adj_close"])

    if len(df) < 5:
        return 0

    # DB'deki mevcut veriyle birleştirerek Z-Score hesapla
    mevcut = pd.read_sql("""
        SELECT price_date, adj_close FROM minerva_signals
        WHERE stock_id = %s
        ORDER BY price_date
    """, conn, params=(stock_id,))

    mevcut["price_date"] = pd.to_datetime(mevcut["price_date"])
    df["price_date"] = pd.to_datetime(df["price_date"])

    # Birleştir, yeni günleri ekle
    birlesik = pd.concat([mevcut, df]).drop_duplicates(
        subset="price_date", keep="last"
    ).sort_values("price_date").reset_index(drop=True)

    # Tüm seri üzerinden Z-Score hesapla
    birlesik["log_getiri"] = np.log(birlesik["adj_close"] / birlesik["adj_close"].shift(1))
    birlesik["z_log_60"]   = klasik_zscore(birlesik["log_getiri"], 60)
    birlesik["z_log_120"]  = klasik_zscore(birlesik["log_getiri"], 120)
    birlesik["rz_log_60"]  = robust_zscore(birlesik["log_getiri"], 60)
    birlesik["rz_log_120"] = robust_zscore(birlesik["log_getiri"], 120)

    # Sadece son 130 günü yaz (gerisi zaten var)
    son_130 = birlesik.tail(130)

    cur = conn.cursor()
    eklenen = 0

    def safe(v):
        return None if (v is None or (isinstance(v, float) and np.isnan(v))) else float(v)

    for _, satir in son_130.iterrows():
        try:
            cur.execute("""
                INSERT INTO minerva_signals
                    (stock_id, price_date, adj_close, log_getiri,
                     z_log_60, z_log_120, rz_log_60, rz_log_120)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (stock_id, price_date) DO UPDATE SET
                    adj_close  = EXCLUDED.adj_close,
                    log_getiri = EXCLUDED.log_getiri,
                    z_log_60   = EXCLUDED.z_log_60,
                    z_log_120  = EXCLUDED.z_log_120,
                    rz_log_60  = EXCLUDED.rz_log_60,
                    rz_log_120 = EXCLUDED.rz_log_120
            """, (
                stock_id,
                satir["price_date"].date(),
                safe(satir["adj_close"]),
                safe(satir["log_getiri"]),
                safe(satir["z_log_60"]),
                safe(satir["z_log_120"]),
                safe(satir["rz_log_60"]),
                safe(satir["rz_log_120"]),
            ))
            eklenen += 1
        except Exception as e:
            print(f"  {symbol} satır hatası: {e}")
            continue

    conn.commit()
    cur.close()
    return eklenen


if __name__ == "__main__":
    print("Minerva Günlük Güncelleme Başladı...")
    print("=" * 60)

    hisseler = hisseleri_cek()
    print(f"{len(hisseler)} hisse güncellenecek.\n")

    toplam = 0
    for stock_id, symbol in hisseler:
        try:
            eklenen = hisse_guncelle(stock_id, symbol)
            print(f"{symbol}: {eklenen} satır güncellendi.")
            toplam += eklenen
        except Exception as e:
            print(f"{symbol}: HATA — {e}")

    print("=" * 60)
    print(f"Tamamlandı. Toplam {toplam} satır güncellendi.")
    conn.close()
