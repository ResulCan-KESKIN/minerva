# anomali_tespit.py — ATR Entegreli Robust Anomali Tespit Sistemi
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
# 1. ATR Hesaplama
# ─────────────────────────────────────────────
def atr_hesapla(df: pd.DataFrame, periyot: int = ATR_PERIYOT) -> pd.DataFrame:
    """
    TR = max(High-Low, |High-Close_prev|, |Low-Close_prev|)
    ATR = Wilder's smoothing (EWM alpha=1/n)
    """
    prev_close = df["kapanis"].shift(1)

    df["tr"] = np.maximum(
        df["yuksek"] - df["dusuk"],
        np.maximum(
            (df["yuksek"] - prev_close).abs(),
            (df["dusuk"] - prev_close).abs()
        )
    )

    # Wilder smoothing = EWM com=periyot-1
    df["atr"] = df["tr"].ewm(com=periyot - 1, min_periods=periyot).mean()

    # Göreceli Volatilite: fiyat hareketini ATR ile normalize et
    df["goreceli_volatilite"] = df["tr"] / df["atr"].replace(0, np.nan)

    return df


# ─────────────────────────────────────────────
# 2. Robust Z-Score (MAD tabanlı)
# ─────────────────────────────────────────────
def robust_zscore(seri: pd.Series, pencere: int) -> pd.Series:
    """
    Robust Z-Score = (x - rolling_median) / (1.4826 * rolling_MAD)
    1.4826 → MAD'ı normal dağılım std'sine ölçekler
    """
    medyan = seri.rolling(pencere, min_periods=pencere // 2).median()
    mad = seri.rolling(pencere, min_periods=pencere // 2).apply(
        lambda x: np.median(np.abs(x - np.median(x))), raw=True
    )
    return (seri - medyan) / (1.4826 * mad.replace(0, np.nan))


# ─────────────────────────────────────────────
# 3. Ana Tarama Fonksiyonu
# ─────────────────────────────────────────────
def anomali_tara(hisse_kodu: str):
    # Ham fiyat verisini çek (ATR için high/low/close/volume lazım)
    df = pd.read_sql("""
        SELECT
            zaman::date AS tarih,
            acilis, kapanis, yuksek, dusuk, hacim
        FROM hisse_fiyatlari
        WHERE hisse_kodu = %s
        ORDER BY zaman
    """, conn, params=(hisse_kodu,))

    if len(df) < 60:
        print(f"{hisse_kodu}: Yeterli veri yok, atlanıyor.")
        return

    df["tarih"] = pd.to_datetime(df["tarih"])

    # Günlük gruplama
    df = df.groupby("tarih").agg(
        acilis=("acilis", "first"),
        yuksek=("yuksek", "max"),
        dusuk=("dusuk", "min"),
        kapanis=("kapanis", "last"),
        hacim=("hacim", "sum")
    ).reset_index()

    # ── ATR hesapla ──
    df = atr_hesapla(df, ATR_PERIYOT)

    # ── Temel feature'lar ──
    df["getiri"] = df["kapanis"].pct_change()
    df["hacim_ort_20g"] = df["hacim"].rolling(20).mean()
    df["rvol"] = df["hacim"] / df["hacim_ort_20g"].replace(0, np.nan)
    df["fiyat_degisimi_5g"] = df["kapanis"].pct_change(5)
    df["volatilite_5g"] = df["getiri"].rolling(5).std()

    # ── Robust Z-Score: 60 ve 120 günlük pencere ──
    for pencere in [60, 120]:
        df[f"rz_atr_{pencere}"] = robust_zscore(df["atr"], pencere)
        df[f"rz_rvol_{pencere}"] = robust_zscore(df["rvol"], pencere)
        df[f"rz_volatilite_{pencere}"] = robust_zscore(df["volatilite_5g"], pencere)

    df = df.dropna()
    if len(df) < 10:
        print(f"{hisse_kodu}: dropna sonrası yeterli satır yok.")
        return

    # ── Kesin anomali: herhangi bir Robust Z-Score %95 eşiği aşıyor mu ──
    # Eşik: |rz| > 2.0 → dağılımın dışındaki ~%5'lik dilim
    rz_kolonlar = [c for c in df.columns if c.startswith("rz_")]
    df["rz_max"] = df[rz_kolonlar].abs().max(axis=1)
    df["kesin_anomali"] = df["rz_max"] > 2.0

    # ── Isolation Forest: RobustScaler ile ──
    feature_kolonlar = [
        "fiyat_degisimi_5g", "volatilite_5g",
        "atr", "goreceli_volatilite",
        "rvol",
        "rz_atr_60", "rz_rvol_60", "rz_volatilite_60",
        "rz_atr_120", "rz_rvol_120", "rz_volatilite_120"
    ]

    X = df[feature_kolonlar].copy()
    scaler = RobustScaler()          # ← StandardScaler yerine RobustScaler
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(contamination=0.05, random_state=42)  # %5 hedef
    df["if_tahmin"] = model.fit_predict(X_scaled)
    df["if_skor"] = model.score_samples(X_scaled)

    # Kesin anomalileri IF'e de yansıt
    df.loc[df["kesin_anomali"], "if_tahmin"] = -1

    # ── Tip belirleme ──
    # kesin_anomali=True → "kesin_anomali"
    # IF=-1 ama rz_max düşük → "soft_anomali"
    anomaliler = df[df["if_tahmin"] == -1].copy()
    anomaliler["tip"] = anomaliler.apply(
        lambda r: "kesin_anomali" if r["kesin_anomali"] else "soft_anomali",
        axis=1
    )

    kesin = anomaliler["tip"].eq("kesin_anomali").sum()
    soft = anomaliler["tip"].eq("soft_anomali").sum()
    print(f"{hisse_kodu}: {len(anomaliler)} anomali ({kesin} kesin, {soft} soft)")

    # ── DB'ye yaz ──
    cur = conn.cursor()
    for _, satir in anomaliler.iterrows():
        cur.execute("""
            SELECT id FROM anomali_kayitlari
            WHERE hisse_kodu = %s AND baslangic_zaman::date = %s
        """, (hisse_kodu, satir["tarih"].date()))

        if cur.fetchone() is None:
            cur.execute("""
                INSERT INTO anomali_kayitlari
                    (hisse_kodu, anomali_tipi, skor, baslangic_zaman, durum)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                hisse_kodu,
                satir["tip"],
                float(satir["if_skor"]),
                satir["tarih"],
                "beklemede"
            ))
    conn.commit()
    cur.close()


if __name__ == "__main__":
    print("Robust ATR anomali taraması başladı...")
    for hisse in HISSELER:
        anomali_tara(hisse)
    print("Tarama tamamlandı.")
    conn.close()