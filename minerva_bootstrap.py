# minerva_bootstrap_toplu.py — Tüm hisseleri toplu çek
import psycopg2
import pandas as pd
import numpy as np
import yfinance as yf
import time
import warnings

warnings.filterwarnings('ignore')

DB_CONFIG = {
    "host": "aws-0-eu-west-1.pooler.supabase.com",
    "port": 6543,
    "database": "postgres",
    "user": "postgres.ewetkqwkjbmblutbejsh",
    "password": "QuantShine2025."
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


def hisseleri_cek() -> list[tuple[int, str]]:
    cur = conn.cursor()
    cur.execute("SELECT id, symbol FROM stocks WHERE is_active = true ORDER BY symbol")
    hisseler = cur.fetchall()
    cur.close()
    return hisseler


def db_yaz(stock_id: int, df: pd.DataFrame):
    cur = conn.cursor()
    eklenen = 0
    for _, satir in df.iterrows():
        def safe(v):
            return None if (v is None or (isinstance(v, float) and np.isnan(v))) else float(v)
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
                satir["price_date"],
                safe(satir["adj_close"]),
                safe(satir["log_getiri"]),
                safe(satir["z_log_60"]),
                safe(satir["z_log_120"]),
                safe(satir["rz_log_60"]),
                safe(satir["rz_log_120"]),
            ))
            eklenen += 1
        except Exception as e:
            print(f"  Satır hatası: {e}")
            continue
    conn.commit()
    cur.close()
    return eklenen


if __name__ == "__main__":
    print("Minerva Bootstrap — Toplu Adj Close Çekme")
    print("=" * 60)

    tablo_olustur()
    hisseler = hisseleri_cek()
    print(f"{len(hisseler)} hisse işlenecek.\n")

    # 50'şer gruplar halinde çek
    GRUP = 50
    toplam_eklenen = 0
    hatali = []

    for i in range(0, len(hisseler), GRUP):
        grup = hisseler[i:i + GRUP]
        tickerlar = [f"{s}.IS" for _, s in grup]
        id_map = {f"{s}.IS": sid for sid, s in grup}

        print(f"Grup {i//GRUP + 1}: {tickerlar[0]} → {tickerlar[-1]} çekiliyor...")

        try:
            raw = yf.download(
                tickerlar,
                period="10y",
                auto_adjust=True,
                group_by="ticker",
                progress=False,
                threads=True
            )
        except Exception as e:
            print(f"  Grup hatası: {e}")
            hatali.extend([s for _, s in grup])
            continue

        for ticker, stock_id in id_map.items():
            try:
                # Tek hisse veya çoklu hisse formatı
                if len(tickerlar) == 1:
                    df = raw[["Close"]].copy()
                else:
                    if ticker not in raw.columns.get_level_values(0):
                        continue
                    df = raw[ticker][["Close"]].copy()

                df.columns = ["adj_close"]
                df.index = pd.to_datetime(df.index).tz_localize(None)
                df["price_date"] = df.index.date
                df = df.reset_index(drop=True).dropna(subset=["adj_close"])

                if len(df) < 60:
                    continue

                df["log_getiri"] = np.log(df["adj_close"] / df["adj_close"].shift(1))
                df["z_log_60"]   = klasik_zscore(df["log_getiri"], 60)
                df["z_log_120"]  = klasik_zscore(df["log_getiri"], 120)
                df["rz_log_60"]  = robust_zscore(df["log_getiri"], 60)
                df["rz_log_120"] = robust_zscore(df["log_getiri"], 120)
                df = df.dropna(subset=["log_getiri"])

                eklenen = db_yaz(stock_id, df)
                symbol = ticker.replace(".IS", "")
                print(f"  {symbol}: {eklenen} satır")
                toplam_eklenen += eklenen

            except Exception as e:
                print(f"  {ticker} hatası: {e}")
                hatali.append(ticker)

        # Gruplar arası bekleme
        time.sleep(3)

    print("=" * 60)
    print(f"Tamamlandı. Toplam {toplam_eklenen} satır eklendi.")
    if hatali:
        print(f"Hatalı ({len(hatali)}): {hatali}")
    conn.close()
