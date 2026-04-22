# anomali_tespit_ext.py — volume_analysis tablosundan Z-Score anomali tespiti
# Yöntem: ≥120g → ECDF 4 seri | 60-119g → ECDF 60g | 0-59g → t-dağılımı
import psycopg2
import psycopg2.pool
import pandas as pd
import numpy as np
from scipy import stats
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import warnings
import time

warnings.filterwarnings('ignore')

EXT_CONFIG = {
    "host": os.environ["EXT_DB_HOST"],
    "port": int(os.environ["EXT_DB_PORT"]),
    "database": os.environ["EXT_DB_NAME"],
    "user": os.environ["EXT_DB_USER"],
    "password": os.environ["EXT_DB_PASSWORD"],
}

ZSCORE_4 = [
    ("z_score_60",         "anomali_z60"),
    ("z_score_120",        "anomali_z120"),
    ("z_score_robust_60",  "anomali_rz60"),
    ("z_score_robust_120", "anomali_rz120"),
]

ZSCORE_60 = [
    ("z_score_60",        "anomali_z60"),
    ("z_score_robust_60", "anomali_rz60"),
]

PENCERE = {"60": 60, "120": 120}
MAX_WORKERS = 4  # Paralel hisse sayısı


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 1 — VERİ ÇEKME
# ═══════════════════════════════════════════════════════════════

def get_conn():
    return psycopg2.connect(**EXT_CONFIG)


def hisseleri_cek() -> list[tuple[int, str]]:
    conn = get_conn()
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
    conn.close()
    return hisseler


def islenmis_hisseler() -> set[str]:
    """Zaten anomali_kayitlari'nda olan hisseleri döndür."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT hisse_kodu FROM anomali_kayitlari")
    hisseler = {r[0] for r in cur.fetchall()}
    cur.close()
    conn.close()
    return hisseler


def zscore_verisi_cek(conn, stock_id: int) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT price_date, z_score_60, z_score_120,
               z_score_robust_60, z_score_robust_120
        FROM volume_analysis
        WHERE stock_id = %s
        ORDER BY price_date
    """, conn, params=(stock_id,))


def fiyat_verisi_cek(conn, stock_id: int) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT price_date, close_price
        FROM stock_prices
        WHERE stock_id = %s
        ORDER BY price_date
    """, conn, params=(stock_id,))


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 2 — ANOMALİ TESPİTİ
# ═══════════════════════════════════════════════════════════════

def _kaydet_toplu(cur, kayitlar: list) -> int:
    """Tüm anomalileri tek sorguda yaz."""
    if not kayitlar:
        return 0

    args = []
    for symbol, tip, skor, tarih, kaynak in kayitlar:
        args.append((symbol, tip, float(skor), tarih, "beklemede", kaynak))

    cur.executemany("""
        INSERT INTO anomali_kayitlari
            (hisse_kodu, anomali_tipi, skor, baslangic_zaman, durum, kaynak)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, args)
    return cur.rowcount


def _ecdf_anomaliler(df_tam: pd.DataFrame, df_yeni: pd.DataFrame, tanimlar: list) -> list:
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


def _t_dagilimi_anomaliler(conn, stock_id: int, df_yeni: pd.DataFrame) -> list:
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


def anomali_tara(stock_id: int, symbol: str) -> str:
    """Her hisse için ayrı bağlantı açar — paralel çalışmaya uygun."""
    try:
        conn = get_conn()
        df_tam = zscore_verisi_cek(conn, stock_id)
        n = len(df_tam)

        if n == 0:
            conn.close()
            return f"{symbol}: Veri yok."

        df_tam["price_date"] = pd.to_datetime(df_tam["price_date"])
        df_yeni = df_tam.copy()  # İlk çalışmada tüm geçmiş

        if df_yeni.empty:
            conn.close()
            return f"{symbol}: Yeni veri yok."

        if n >= 120:
            anomaliler = _ecdf_anomaliler(df_tam, df_yeni, ZSCORE_4)
            mod = "ECDF 4 seri"
        elif n >= 60:
            anomaliler = _ecdf_anomaliler(df_tam, df_yeni, ZSCORE_60)
            mod = "ECDF 60g"
        else:
            anomaliler = _t_dagilimi_anomaliler(conn, stock_id, df_yeni)
            mod = "t-dağılımı"

        # Kayıtları ekle
        kayitlar = [(symbol, tip, skor, tarih, kaynak) for tip, skor, tarih, kaynak in anomaliler]

        cur = conn.cursor()
        toplam = _kaydet_toplu(cur, kayitlar)
        conn.commit()
        cur.close()
        conn.close()

        return f"{symbol} [{mod}]: {toplam} anomali kaydedildi."

    except Exception as e:
        return f"{symbol}: HATA — {e}"


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 3 — ÇALIŞTIR
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Minerva Anomali Tespiti Başladı...")
    print("=" * 60)

    hisseler = hisseleri_cek()
    islenmis = islenmis_hisseler()

    # Daha önce işlenenleri atla
    bekleyen = [(sid, sym) for sid, sym in hisseler if sym not in islenmis]
    atlanan = len(hisseler) - len(bekleyen)

    print(f"Toplam: {len(hisseler)} | Atlanıyor: {atlanan} | İşlenecek: {len(bekleyen)}\n")

    # Paralel çalıştır
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(anomali_tara, sid, sym): sym for sid, sym in bekleyen}
        for i, future in enumerate(as_completed(futures), 1):
            sonuc = future.result()
            print(f"[{i}/{len(bekleyen)}] {sonuc}")

    print("=" * 60)
    print("Tarama tamamlandı.")
