# minerva_guncelle.py — Günlük adj close toplu çekme ve Z-Score güncelleme
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
GRUP_BOYUTU = 50


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


def mevcut_veri_cek(stock_id: int) -> pd.DataFrame:
    """DB'deki son 130 günlük adj_close verisini çek."""
    return pd.read_sql("""
        SELECT price_date, adj_close FROM minerva_signals
        WHERE stock_id = %s
        ORDER BY price_date DESC
        LIMIT 130
    """, conn, params=(stock_id,))


def db_yaz(stock_id: int, df: pd.DataFrame) -> int:
    cur = conn.cursor()
    eklenen = 0

    def safe(v):
        return None if (v is None or (isinstance(v, float) and np.isnan(v))) else float(v)

    for _, satir in df.iterrows():
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
                satir["price_date"].date() if hasattr(satir["price_date"], "date") else satir["price_date"],
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


def grup_isle(grup: list[tuple[int, str]]) -> int:
    """50 hisseyi toplu çek, hesapla, yaz."""
    tickerlar = [f"{s}.IS" for _, s in grup]
    id_map = {f"{s}.IS": sid for sid, s in grup}

    try:
        raw = yf.download(
            tickerlar,
            period="130d",
            auto_adjust=True,
            group_by="ticker",
            progress=False,
            threads=True
        )
    except Exception as e:
        print(f"  Grup çekme hatası: {e}")
        return 0

    toplam = 0

    for ticker, stock_id in id_map.items():
        symbol = ticker.replace(".IS", "")
        try:
            # Tek veya çoklu hisse formatı
            if len(tickerlar) == 1:
                yeni = raw[["Close"]].copy()
            else:
                if ticker not in raw.columns.get_level_values(0):
                    print(f"  {symbol}: Veri yok.")
                    continue
                yeni = raw[ticker][["Close"]].copy()

            yeni.columns = ["adj_close"]
            yeni.index = pd.to_datetime(yeni.index).tz_localize(None)
            yeni["price_date"] = pd.to_datetime(yeni.index.date)
            yeni = yeni.reset_index(drop=True).dropna(subset=["adj_close"])

            if yeni.empty:
                continue

            # DB'deki mevcut veriyle birleştir
            mevcut = mevcut_veri_cek(stock_id)
            mevcut["price_date"] = pd.to_datetime(mevcut["price_date"])

            birlesik = pd.concat([mevcut, yeni]).drop_duplicates(
                subset="price_date", keep="last"
            ).sort_values("price_date").reset_index(drop=True)

            # Z-Score hesapla
            birlesik["log_getiri"] = np.log(birlesik["adj_close"] / birlesik["adj_close"].shift(1))
            birlesik["z_log_60"]   = klasik_zscore(birlesik["log_getiri"], 60)
            birlesik["z_log_120"]  = klasik_zscore(birlesik["log_getiri"], 120)
            birlesik["rz_log_60"]  = robust_zscore(birlesik["log_getiri"], 60)
            birlesik["rz_log_120"] = robust_zscore(birlesik["log_getiri"], 120)

            # Sadece son 5 günü yaz (yeni günler)
            son_5 = birlesik.tail(5)
            eklenen = db_yaz(stock_id, son_5)
            print(f"  {symbol}: {eklenen} satır güncellendi.")
            toplam += eklenen

        except Exception as e:
            print(f"  {symbol}: HATA — {e}")

    return toplam


if __name__ == "__main__":
    print("Minerva Günlük Güncelleme Başladı (Toplu Çekme)...")
    print("=" * 60)

    hisseler = hisseleri_cek()
    print(f"{len(hisseler)} hisse güncellenecek.\n")

    toplam = 0
    for i in range(0, len(hisseler), GRUP_BOYUTU):
        grup = hisseler[i:i + GRUP_BOYUTU]
        print(f"Grup {i//GRUP_BOYUTU + 1}: {grup[0][1]} → {grup[-1][1]}")
        toplam += grup_isle(grup)
        time.sleep(2)

    print("=" * 60)
    print(f"Tamamlandı. Toplam {toplam} satır güncellendi.")
    conn.close()
