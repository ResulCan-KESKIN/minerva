"""
Faz 3 — Kutu içindeki hacim anomali şoklarını say.
Faz 4 — Toplam kutu hacminin yüzde kaçı şok günlerinden geldi?
"""

from __future__ import annotations
import pandas as pd
from dataclasses import dataclass


@dataclass
class SokSonucu:
    sok_sayisi:          int
    sok_hacim_yuzdesi:   float   # 0–100 arası yüzde


def faz3_faz4_hesapla(
    df_tam: pd.DataFrame,
    anomali_tarihleri: set,
    kutu_baslangic: pd.Timestamp,
    kutu_bitis: pd.Timestamp,
    kutu_hacim: float,
) -> SokSonucu:
    """
    df_tam            : price_date (index ya da sütun) + hacim sütunlu DataFrame.
    anomali_tarihleri : set of date — minerva_anomali anomali_kayitlari'ndan gelen tarihler.
    kutu_baslangic    : Faz 1 kutu başlangıcı.
    kutu_bitis        : Faz 1 kutu bitişi.
    kutu_hacim        : Faz 2'den gelen toplam kutu hacmi.
    """
    if "price_date" in df_tam.columns:
        df_tam = df_tam.set_index("price_date")
    df_tam = df_tam.sort_index()

    mask = (df_tam.index >= kutu_baslangic) & (df_tam.index <= kutu_bitis)
    df_kutu = df_tam.loc[mask]

    if df_kutu.empty or kutu_hacim <= 0:
        return SokSonucu(sok_sayisi=0, sok_hacim_yuzdesi=0.0)

    # Kutu içindeki şok günleri
    sok_gunler = df_kutu[df_kutu.index.map(lambda t: t.date() in anomali_tarihleri)]
    sok_sayisi = len(sok_gunler)
    sok_hacim  = float(sok_gunler["hacim"].sum()) if not sok_gunler.empty else 0.0

    yuzdesi = (sok_hacim / kutu_hacim * 100) if kutu_hacim > 0 else 0.0

    return SokSonucu(sok_sayisi=sok_sayisi, sok_hacim_yuzdesi=round(yuzdesi, 2))
