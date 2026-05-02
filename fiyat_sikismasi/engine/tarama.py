"""
Ana pipeline — bir hisse için Faz 1-4'ü zincirler ve sonuçları DB'ye yazar.
"""

from __future__ import annotations
import logging
import pandas as pd
from typing import Optional

from engine.radar1 import radar1_tara, KutuSonucu
from engine.radar2 import radar2_tara, Radar2Sonucu
from engine.hacim_olcum import faz2_hesapla
from engine.sok_sayaci import faz3_faz4_hesapla

log = logging.getLogger(__name__)


def _kaydet(cur, stock_id: int, symbol: str, radar: str,
            kutu_bas, kutu_bit, zirve, dip, pencere,
            fiziki, efor, sok_s, sok_y):
    cur.execute("""
        INSERT INTO fiyat_sikismasi_kayitlari
            (stock_id, symbol, radar,
             kutu_baslangic, kutu_bitis,
             cekirdek_zirve, cekirdek_dip,
             pencere_uzunlugu,
             fiziki_limit, efor_rasyosu,
             sok_sayisi, sok_hacim_yuzdesi)
        VALUES (%s,%s,%s, %s,%s, %s,%s, %s, %s,%s, %s,%s)
        ON CONFLICT (stock_id, radar, kutu_baslangic, kutu_bitis) DO UPDATE SET
            cekirdek_zirve    = EXCLUDED.cekirdek_zirve,
            cekirdek_dip      = EXCLUDED.cekirdek_dip,
            pencere_uzunlugu  = EXCLUDED.pencere_uzunlugu,
            fiziki_limit      = EXCLUDED.fiziki_limit,
            efor_rasyosu      = EXCLUDED.efor_rasyosu,
            sok_sayisi        = EXCLUDED.sok_sayisi,
            sok_hacim_yuzdesi = EXCLUDED.sok_hacim_yuzdesi,
            olusturma_zaman   = NOW()
    """, (stock_id, symbol, radar,
          kutu_bas, kutu_bit, zirve, dip, pencere,
          fiziki, efor, sok_s, sok_y))


def hisse_tara(
    conn,
    stock_id: int,
    symbol: str,
    df_fiyat: pd.DataFrame,
    anomali_tarihleri: set,
    dolasim_lot: Optional[float],
) -> int:
    """
    Tek hisse için 4 fazı çalıştır ve DB'ye yaz.
    Döner: kaydedilen kayıt sayısı.
    """
    cur = conn.cursor()
    kayit_sayisi = 0

    # -- Radar 1 --
    r1 = radar1_tara(df_fiyat.copy())
    if r1 is not None:
        h = faz2_hesapla(df_fiyat.copy(), r1.baslangic, r1.bitis, dolasim_lot)
        s = faz3_faz4_hesapla(df_fiyat.copy(), anomali_tarihleri,
                               r1.baslangic, r1.bitis, h.kutu_hacim)
        _kaydet(cur, stock_id, symbol, "radar1",
                r1.baslangic.date(), r1.bitis.date(),
                r1.cekirdek_zirve, r1.cekirdek_dip, r1.pencere_uzunlugu,
                h.fiziki_limit, h.efor_rasyosu,
                s.sok_sayisi, s.sok_hacim_yuzdesi)
        kayit_sayisi += 1
        log.info(f"{symbol} radar1: {r1.pencere_uzunlugu}g kutu "
                 f"[{r1.cekirdek_dip:.2f}–{r1.cekirdek_zirve:.2f}] "
                 f"efor={h.efor_rasyosu} şok={s.sok_sayisi}")

    # -- Radar 2 --
    r2_liste = radar2_tara(df_fiyat.copy(), anomali_tarihleri)
    for r2 in r2_liste:
        h = faz2_hesapla(df_fiyat.copy(), r2.kutu_baslangic, r2.kutu_bitis, dolasim_lot)
        s = faz3_faz4_hesapla(df_fiyat.copy(), anomali_tarihleri,
                               r2.kutu_baslangic, r2.kutu_bitis, h.kutu_hacim)
        _kaydet(cur, stock_id, symbol, "radar2",
                r2.kutu_baslangic.date(), r2.kutu_bitis.date(),
                r2.ust_sinir, r2.alt_sinir, r2.pencere_uzunlugu,
                h.fiziki_limit, h.efor_rasyosu,
                s.sok_sayisi, s.sok_hacim_yuzdesi)
        kayit_sayisi += 1

    conn.commit()
    cur.close()
    return kayit_sayisi
