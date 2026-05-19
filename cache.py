"""
Streamlit cache_data katmanı — sayfalar arası ve rerun'lar arası
veri sorgularını TTL ile cache'ler.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
from db import get_conn
import data_access


_TTL = 300  # 5 dk


@st.cache_data(ttl=_TTL)
def fiyat_verisi(stock_id: int, gun: int = 500) -> pd.DataFrame:
    return data_access.fiyat_verisi_cek(get_conn(), stock_id, gun)


@st.cache_data(ttl=_TTL)
def anomali_tarihleri(symbol: str) -> set:
    return data_access.anomali_tarihleri_cek(get_conn(), symbol)


@st.cache_data(ttl=_TTL)
def sikisma_kayitlari(symbol: str) -> pd.DataFrame:
    return data_access.sikisma_kayitlari_cek(get_conn(), symbol)


@st.cache_data(ttl=_TTL)
def stock_id_lookup(symbol: str) -> int | None:
    df = pd.read_sql(
        "SELECT id FROM stocks WHERE symbol = %s", get_conn(), params=(symbol,)
    )
    return int(df["id"].iloc[0]) if not df.empty else None


@st.cache_data(ttl=_TTL)
def anomali_kayitlari(symbol: str) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT id, baslangic_zaman, anomali_tipi,
               ROUND(skor::numeric,4) AS skor, durum, notlar
        FROM anomali_kayitlari
        WHERE hisse_kodu = %s
        ORDER BY baslangic_zaman DESC
    """, get_conn(), params=(symbol,))


@st.cache_data(ttl=_TTL)
def zscore_seri(stock_id: int, gun: int = 500) -> pd.DataFrame:
    df = pd.read_sql("""
        SELECT price_date AS tarih, z_score_60, z_score_120,
               z_score_robust_60, z_score_robust_120
        FROM volume_analysis
        WHERE stock_id = %s
        ORDER BY price_date DESC
        LIMIT %s
    """, get_conn(), params=(stock_id, gun))
    return df.sort_values("tarih").reset_index(drop=True)


@st.cache_data(ttl=_TTL)
def zscore_son(stock_id: int, n: int = 10) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT price_date, z_score_robust_60, z_score_robust_120
        FROM volume_analysis
        WHERE stock_id = %s
        ORDER BY price_date DESC
        LIMIT %s
    """, get_conn(), params=(stock_id, n))


@st.cache_data(ttl=_TTL)
def radar1_kanallar() -> pd.DataFrame:
    """v2.3 algoritmasının ürettiği tüm radar1 kanalları (kanal_yonu IS NOT NULL)."""
    return pd.read_sql("""
        SELECT symbol, kanal_yonu, pencere_uzunlugu,
               m_norm::float        AS m_norm,
               kutu_baslangic, kutu_bitis,
               efor_rasyosu::float  AS efor_rasyosu,
               sok_sayisi,
               sok_hacim_yuzdesi::float AS sok_hacim_yuzdesi
        FROM fiyat_sikismasi_kayitlari
        WHERE radar = 'radar1' AND kanal_yonu IS NOT NULL
        ORDER BY pencere_uzunlugu DESC, ABS(m_norm) DESC
    """, get_conn())


@st.cache_data(ttl=_TTL)
def liderlik_liste(gun_siniri: int = 90) -> pd.DataFrame:
    """Hisse başına en yüksek skoru seçer; fiziki_limit dahildir. gun_siniri=0 → tüm geçmiş."""
    gun_where = (
        f"WHERE kutu_bitis >= CURRENT_DATE - INTERVAL '{int(gun_siniri)} days'"
        if gun_siniri > 0 else ""
    )
    return pd.read_sql(f"""
        WITH filtered AS (
            SELECT * FROM fiyat_sikismasi_kayitlari {gun_where}
        ),
        RankedSqueezes AS (
            SELECT
                symbol, radar, kanal_yonu,
                efor_rasyosu::float      AS efor_rasyosu,
                sok_sayisi,
                sok_hacim_yuzdesi::float AS sok_hacim_yuzdesi,
                pencere_uzunlugu,
                kutu_baslangic, kutu_bitis,
                fiziki_limit::float      AS fiziki_limit,
                milat_tipi, kopus_yonu,
                fiyat_avwap_sapma::float AS fiyat_avwap_sapma,
                ((COALESCE(efor_rasyosu,0) * 2)
                 + (COALESCE(sok_sayisi,0) * 3)
                 + (COALESCE(sok_hacim_yuzdesi,0) / 10.0)) AS master_skor,
                ROW_NUMBER() OVER(
                    PARTITION BY symbol
                    ORDER BY ((COALESCE(efor_rasyosu,0) * 2)
                              + (COALESCE(sok_sayisi,0) * 3)
                              + (COALESCE(sok_hacim_yuzdesi,0) / 10.0)) DESC
                ) AS rn
            FROM filtered
        ),
        RadarAgg AS (
            SELECT symbol, string_agg(DISTINCT radar, '+') AS radars
            FROM filtered
            GROUP BY symbol
        )
        SELECT
            r.symbol, ra.radars, r.kanal_yonu,
            r.efor_rasyosu, r.sok_sayisi, r.sok_hacim_yuzdesi,
            r.pencere_uzunlugu, r.kutu_baslangic, r.kutu_bitis,
            r.fiziki_limit, r.master_skor,
            r.milat_tipi, r.kopus_yonu, r.fiyat_avwap_sapma
        FROM RankedSqueezes r
        JOIN RadarAgg ra ON r.symbol = ra.symbol
        WHERE r.rn = 1
        ORDER BY r.master_skor DESC
    """, get_conn())


def anomali_mutasyon_sonrasi(symbol: str):
    """Anomali UPDATE sonrası ilgili cache'leri temizle."""
    anomali_kayitlari.clear()
    anomali_tarihleri.clear()
