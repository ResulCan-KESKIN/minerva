"""
Faz 1 Radar 1 — Geçmişe dönük köpük toleranslı kutu tespiti.

Algoritma:
  1. 60 günlük baz pencereyi test et.
  2. Başarılıysa → 70, 80, 90... gün geriye genişlet (operasyon başlangıcını bul).
  3. Başarısızsa → 50, 40, 30, 20, 10 güne daralt (mikro sıkışma ara).
  Sonuç: en geniş/dar geçerli pencere veya None.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


SIKISMA_ESIGI   = 0.15   # %15 fiyat aralığı
KOPUK_ORAN      = 0.10   # toplam günlerin %10'u köpük sayılır
BAZ_GUN         = 60
GENISLEME_ADIM  = 10
MIN_PENCERE     = 10
MAX_PENCERE     = 200    # mantıklı bir üst sınır


@dataclass
class KutuSonucu:
    baslangic:       pd.Timestamp
    bitis:           pd.Timestamp
    cekirdek_zirve:  float
    cekirdek_dip:    float
    pencere_uzunlugu: int
    kopuk_gunler:    list = field(default_factory=list)   # köpük gün tarihleri


def _kutu_test(df_pencere: pd.DataFrame) -> Optional[KutuSonucu]:
    """
    Verilen penceredeki DataFrame için köpük toleranslı kutu hesapla.
    df_pencere: price_date index'li, 'kapanis' sütunlu DataFrame.
    Geçersizse None döner.
    """
    n = len(df_pencere)
    if n < MIN_PENCERE:
        return None

    kopuk_n = max(1, round(n * KOPUK_ORAN))

    # Medyandan mutlak sapma — en aşırı %10'u köpük say
    medyan = df_pencere["kapanis"].median()
    sapma  = (df_pencere["kapanis"] - medyan).abs()
    kopuk_idx = sapma.nlargest(kopuk_n).index

    cekirdek = df_pencere.loc[~df_pencere.index.isin(kopuk_idx), "kapanis"]
    if cekirdek.empty:
        return None

    zirve = cekirdek.max()
    dip   = cekirdek.min()

    if dip <= 0:
        return None

    aralik = (zirve - dip) / dip
    if aralik > SIKISMA_ESIGI:
        return None

    return KutuSonucu(
        baslangic=df_pencere.index[0],
        bitis=df_pencere.index[-1],
        cekirdek_zirve=float(zirve),
        cekirdek_dip=float(dip),
        pencere_uzunlugu=n,
        kopuk_gunler=kopuk_idx.tolist(),
    )


def radar1_tara(df: pd.DataFrame) -> Optional[KutuSonucu]:
    """
    df: 'price_date' (ya da index), 'kapanis' sütunları olan DataFrame.
        Tarih sıralı olmalı (eskiden yeniye).

    Döner: KutuSonucu veya None.
    """
    if "price_date" in df.columns:
        df = df.set_index("price_date")
    df = df.sort_index()

    if len(df) < MIN_PENCERE:
        return None

    # -- Baz test: son 60 gün --
    baz = df.iloc[-BAZ_GUN:] if len(df) >= BAZ_GUN else df
    baz_sonuc = _kutu_test(baz)

    if baz_sonuc is not None:
        # Başarılı → genişleme: 70, 80, 90... gün geriye git
        son_gecerli = baz_sonuc
        pencere = BAZ_GUN + GENISLEME_ADIM
        while pencere <= min(len(df), MAX_PENCERE):
            aday = df.iloc[-pencere:]
            sonuc = _kutu_test(aday)
            if sonuc is None:
                break
            son_gecerli = sonuc
            pencere += GENISLEME_ADIM
        return son_gecerli
    else:
        # Başarısız → daralma: 50, 40, 30, 20, 10 gün
        pencere = BAZ_GUN - GENISLEME_ADIM
        while pencere >= MIN_PENCERE:
            aday = df.iloc[-pencere:] if len(df) >= pencere else df
            sonuc = _kutu_test(aday)
            if sonuc is not None:
                return sonuc
            pencere -= GENISLEME_ADIM
        return None
