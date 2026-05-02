"""
DB sorgular — OHLCV, anomali tarihleri, dolaşım lot, kayıt listesi.
"""

from __future__ import annotations
import pandas as pd
from db import get_conn


def fiyat_verisi_cek(conn, stock_id: int, gun: int = 250) -> pd.DataFrame:
    """Son `gun` günlük OHLCV verisi döner."""
    df = pd.read_sql("""
        SELECT price_date,
               open_price  AS acilis,
               high_price  AS yuksek,
               low_price   AS dusuk,
               close_price AS kapanis,
               volume      AS hacim
        FROM stock_prices
        WHERE stock_id = %s
        ORDER BY price_date DESC
        LIMIT %s
    """, conn, params=(stock_id, gun))
    df["price_date"] = pd.to_datetime(df["price_date"])
    return df.sort_values("price_date").reset_index(drop=True)


def anomali_tarihleri_cek(conn, symbol: str) -> set:
    """Hisse için kayıtlı tüm hacim anomalisi tarihlerini set olarak döner."""
    df = pd.read_sql("""
        SELECT baslangic_zaman::date AS tarih
        FROM anomali_kayitlari
        WHERE hisse_kodu = %s
    """, conn, params=(symbol,))
    return set(df["tarih"].tolist())


def dolasim_lot_cek(conn, stock_id: int) -> float | None:
    try:
        cur = conn.cursor()
        cur.execute("SELECT dolasim_lot FROM stocks WHERE id = %s", (stock_id,))
        row = cur.fetchone()
        cur.close()
        return float(row[0]) if row and row[0] else None
    except Exception:
        conn.rollback()
        return None


def hisse_listesi_cek(conn) -> pd.DataFrame:
    """id, symbol sütunlu aktif hisse listesi."""
    return pd.read_sql(
        "SELECT id, symbol FROM stocks WHERE is_active = true ORDER BY symbol", conn
    )


def sikisma_kayitlari_cek(conn, symbol: str | None = None) -> pd.DataFrame:
    """
    Tüm sıkışma kayıtları; symbol verilirse filtreli döner.
    Son kutu_bitis'e göre sıralı.
    """
    sql = """
        SELECT id, symbol, radar, kutu_baslangic, kutu_bitis,
               cekirdek_zirve, cekirdek_dip, pencere_uzunlugu,
               fiziki_limit, efor_rasyosu,
               sok_sayisi, sok_hacim_yuzdesi, olusturma_zaman
        FROM fiyat_sikismasi_kayitlari
        {where}
        ORDER BY kutu_bitis DESC, efor_rasyosu DESC NULLS LAST
    """
    if symbol:
        return pd.read_sql(
            sql.format(where="WHERE symbol = %s"), conn, params=(symbol,)
        )
    return pd.read_sql(sql.format(where=""), conn)


def ozet_metrikler_cek(conn) -> dict:
    df = pd.read_sql("""
        SELECT
            (SELECT COUNT(*) FROM stocks WHERE is_active = true)     AS hisse_sayisi,
            COUNT(*)                                                  AS toplam_sikisma,
            COUNT(*) FILTER (WHERE radar = 'radar1')                 AS radar1_sayisi,
            COUNT(*) FILTER (WHERE radar = 'radar2')                 AS radar2_sayisi,
            MAX(kutu_bitis)                                           AS son_guncelleme
        FROM fiyat_sikismasi_kayitlari
    """, conn)
    return df.iloc[0].to_dict()
