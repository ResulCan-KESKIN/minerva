# anomali_tespit.py — Bağımsız Çift-Z ve Robust ATR Sistemi
import psycopg2
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler
import os

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "database": os.environ.get("DB_NAME", "minerva"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "110537")
}

conn = psycopg2.connect(**DB_CONFIG)

HISSELER = [
    "TEHOL.IS", "DERHL.IS", "CRDFA.IS", "ADESE.IS", "DSTKF.IS",
    "VSNMD.IS", "HEDEF.IS", "EMKEL.IS", "ALCTL.IS", "SASA.IS",
    "ASELS.IS", "GZNMI.IS", "BORLS.IS", "SUNTK.IS", "SEGYO.IS"
]

ATR_PERIYOT = 14

# ─────────────────────────────────────────────
# 1. Metrik Fonksiyonları
# ─────────────────────────────────────────────
def klasik_zscore(seri: pd.Series, pencere: int) -> pd.Series:
    """Ortalama ve Standart Sapma tabanlı klasik hesaplama."""
    ort = seri.rolling(pencere, min_periods=pencere // 2).mean()
    std = seri.rolling(pencere, min_periods=pencere // 2).std()
    return (seri - ort) / std.replace(0, np.nan)

def robust_zscore(seri: pd.Series, pencere: int) -> pd.Series:
    """MAD tabanlı uç değerlere dirençli hesaplama."""
    medyan = seri.rolling(pencere, min_periods=pencere // 2).median()
    mad = seri.rolling(pencere, min_periods=pencere // 2).apply(
        lambda x: np.median(np.abs(x - np.median(x))), raw=True
    )
    return (seri - medyan) / (1.4826 * mad.replace(0, np.nan))

def atr_hesapla(df: pd.DataFrame, periyot: int = ATR_PERIYOT) -> pd.DataFrame:
    prev_close = df["kapanis"].shift(1)
    df["tr"] = np.maximum(
        df["yuksek"] - df["dusuk"],
        np.maximum((df["yuksek"] - prev_close).abs(), (df["dusuk"] - prev_close).abs())
    )
    df["atr"] = df["tr"].ewm(com=periyot - 1, min_periods=periyot).mean()
    df["goreceli_volatilite"] = df["tr"] / df["atr"].replace(0, np.nan)
    return df

# ─────────────────────────────────────────────
# 2. Ana Tarama Fonksiyonu
# ─────────────────────────────────────────────
def anomali_tara(hisse_kodu: str):
    df = pd.read_sql("""
        SELECT zaman::date AS tarih, acilis, kapanis, yuksek, dusuk, hacim
        FROM hisse_fiyatlari WHERE hisse_kodu = %s ORDER BY zaman
    """, conn, params=(hisse_kodu,))

    if len(df) < 120: return # 120g pencere için yeterli veri kontrolü

    df["tarih"] = pd.to_datetime(df["tarih"])
    df = df.groupby("tarih").agg(
        acilis=("acilis", "first"), yuksek=("yuksek", "max"),
        dusuk=("dusuk", "min"), kapanis=("kapanis", "last"), hacim=("hacim", "sum")
    ).reset_index()

    df = atr_hesapla(df, ATR_PERIYOT)
    df["getiri"] = df["kapanis"].pct_change()
    df["hacim_ort_20g"] = df["hacim"].rolling(20).mean()
    df["rvol"] = df["hacim"] / df["hacim_ort_20g"].replace(0, np.nan)
    df["volatilite_5g"] = df["getiri"].rolling(5).std()

    # ── 4'lü Bağımsız Z-Hesaplaması ──
    # Hem 60 hem 120 gün; hem Klasik hem Robust
    for p in [60, 120]:
        # ATR üzerinden hesaplamalar
        df[f"kz_atr_{p}"] = klasik_zscore(df["atr"], p)
        df[f"rz_atr_{p}"] = robust_zscore(df["atr"], p)
        # RVOL (Hacim) üzerinden hesaplamalar
        df[f"kz_rvol_{p}"] = klasik_zscore(df["rvol"], p)
        df[f"rz_rvol_{p}"] = robust_zscore(df["rvol"], p)

    df = df.dropna()
    
    # ── Bağımsız Sinyal Toplama ──
    kz_kolonlar = [c for c in df.columns if c.startswith("kz_")]
    rz_kolonlar = [c for c in df.columns if c.startswith("rz_")]
    
    df["kz_max"] = df[kz_kolonlar].abs().max(axis=1)
    df["rz_max"] = df[rz_kolonlar].abs().max(axis=1)
    
    # Herhangi bir skorun eşiği geçmesi (Hassasiyet en baştaki gibi: 2.0)
    df["z_anomali_sinyali"] = (df["kz_max"] > 2.0) | (df["rz_max"] > 2.0)

    # ── Isolation Forest Doğrulaması ──
    feature_kolonlar = ["fiyat_degisimi_5g", "volatilite_5g", "goreceli_volatilite", "rvol"]
    X = df[feature_kolonlar].copy()
    X_scaled = RobustScaler().fit_transform(X)

    # En baştaki hassasiyet: contamination=0.05
    model = IsolationForest(contamination=0.05, random_state=42)
    df["if_tahmin"] = model.fit_predict(X_scaled)
    df["if_skor"] = model.score_samples(X_scaled)

    # ── Karar ve Kayıt ──
    # İster IF yakalasın, ister Z-skorlar yakalasın; hepsini 'anomali' kabul et
    df["anomali_final"] = (df["if_tahmin"] == -1) | (df["z_anomali_sinyali"])
    
    anomaliler = df[df["anomali_final"]].copy()
    
    # Tip Belirleme (Robust Z-Skor uçtuysa 'kesin', diğerleri 'soft')
    anomaliler["tip"] = anomaliler.apply(
        lambda r: "kesin_anomali" if r["rz_max"] > 3.0 else "soft_anomali", axis=1
    )

    print(f"{hisse_kodu}: {len(anomaliler)} anomali bulundu.")

    cur = conn.cursor()
    for _, satir in anomaliler.iterrows():
        cur.execute("""
            SELECT id FROM anomali_kayitlari WHERE hisse_kodu = %s AND baslangic_zaman::date = %s
        """, (hisse_kodu, satir["tarih"].date()))

        if cur.fetchone() is None:
            cur.execute("""
                INSERT INTO anomali_kayitlari (hisse_kodu, anomali_tipi, skor, baslangic_zaman, durum)
                VALUES (%s, %s, %s, %s, %s)
            """, (hisse_kodu, satir["tip"], float(satir["if_skor"]), satir["tarih"], "beklemede"))
    conn.commit()
    cur.close()

if __name__ == "__main__":
    print("Bağımsız Çift-Z Robust Tarama Başladı...")
    for hisse in HISSELER:
        anomali_tara(hisse)
    print("İşlem Tamamlandı.")
    conn.close()