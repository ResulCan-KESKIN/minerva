"""
Faz 2 — Kutu içindeki hacim ölçümü.

  2.1 Fiziki Limit  : kutu_hacim / dolasim_lot
  2.2 Efor Rasyosu  : kutu_hacim / (ADV_k * k)
      ADV_k = hissenin kutu öncesi k günlük ortalama hacmi
"""

from __future__ import annotations
import pandas as pd
from dataclasses import dataclass
from typing import Optional


@dataclass
class HacimSonucu:
    kutu_hacim:     float
    fiziki_limit:   Optional[float]   # None ise dolasim_lot yoktur
    efor_rasyosu:   Optional[float]   # None ise yeterli geçmiş veri yoktur


def faz2_hesapla(
    df_tam: pd.DataFrame,
    kutu_baslangic: pd.Timestamp,
    kutu_bitis: pd.Timestamp,
    dolasim_lot: Optional[float],
) -> HacimSonucu:
    """
    df_tam : price_date (index ya da sütun) + hacim sütunlu tam tarihsel veri.
    kutu_baslangic / kutu_bitis : sıkışma kutusunun sınırları.
    dolasim_lot : stocks.dolasim_lot değeri (yoksa None).
    """
    if "price_date" in df_tam.columns:
        df_tam = df_tam.set_index("price_date")
    df_tam = df_tam.sort_index()

    # Kutu içi günler
    mask = (df_tam.index >= kutu_baslangic) & (df_tam.index <= kutu_bitis)
    df_kutu = df_tam.loc[mask]
    if df_kutu.empty:
        return HacimSonucu(kutu_hacim=0.0, fiziki_limit=None, efor_rasyosu=None)

    kutu_hacim = float(df_kutu["hacim"].sum())
    pencere_k  = len(df_kutu)

    # 2.1 Fiziki Limit
    fiziki = None
    if dolasim_lot and dolasim_lot > 0:
        fiziki = kutu_hacim / dolasim_lot

    # 2.2 Efor Rasyosu — kutu öncesi k güne bak
    efor = None
    df_oncesi = df_tam.loc[df_tam.index < kutu_baslangic]
    if len(df_oncesi) >= pencere_k:
        adv = float(df_oncesi["hacim"].iloc[-pencere_k:].mean())
        if adv > 0:
            # Kutu toplam hacmi vs kutu uzunluğundaki "normal" hacim
            efor = kutu_hacim / (adv * pencere_k)

    return HacimSonucu(
        kutu_hacim=kutu_hacim,
        fiziki_limit=fiziki,
        efor_rasyosu=efor,
    )
