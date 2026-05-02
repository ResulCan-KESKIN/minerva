"""
Faz 1 Radar 2 — Olay tetikli kutu tespiti.

Devasa hacim anomalisi olan günleri "milat" kabul eder:
  - Tavan kapanışı (+%10) → pas geç (dağıtım/momentum rallisi)
  - Taban kapanışı (-%10) veya savaş mumu → çıpala:
      üst = dünkü kapanış, alt = bugünkü dip
  Sonraki günlerde kutu kırılana kadar aktif tutulur; kırılınca kapatılır.
"""

from __future__ import annotations
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional


TAVAN_ESIGI        = 0.09    # +%9 üstü tavan sayılır
TABAN_ESIGI        = -0.09   # -%9 altı taban sayılır
SAVAS_MUMU_FITIL   = 3.0     # (high-low) >= 3 * |close-open|
SAVAS_MUMU_GOVDE   = 0.30    # |close-open| / (high-low) <= 0.30


@dataclass
class Radar2Sonucu:
    olay_tarihi:     pd.Timestamp
    kutu_baslangic:  pd.Timestamp
    kutu_bitis:      pd.Timestamp
    ust_sinir:       float          # dünkü kapanış
    alt_sinir:       float          # bugünkü dip
    pencere_uzunlugu: int
    kirilis_tarihi:  Optional[pd.Timestamp] = None


def _savas_mumu_mu(row: pd.Series) -> bool:
    govde = abs(row["kapanis"] - row["acilis"])
    aralik = row["yuksek"] - row["dusuk"]
    if aralik <= 0:
        return False
    return (aralik >= SAVAS_MUMU_FITIL * govde) and (govde / aralik <= SAVAS_MUMU_GOVDE)


def _gun_degisim(kapanis: float, dunku_kapanis: float) -> float:
    if dunku_kapanis <= 0:
        return 0.0
    return (kapanis - dunku_kapanis) / dunku_kapanis


def radar2_tara(df: pd.DataFrame, anomali_tarihleri: set) -> list[Radar2Sonucu]:
    """
    df: price_date (index ya da sütun), acilis/yuksek/dusuk/kapanis/hacim sütunları.
    anomali_tarihleri: set of date objects — minerva_anomali'den gelen hacim anomalisi günleri.

    Döner: Radar2Sonucu listesi (kutu başına bir kayıt).
    """
    if "price_date" in df.columns:
        df = df.set_index("price_date")
    df = df.sort_index()

    sonuclar: list[Radar2Sonucu] = []
    aktif_kutular: list[dict] = []  # {ust, alt, baslangic, olay}

    tarihler = df.index.tolist()

    for i, tarih in enumerate(tarihler):
        row = df.loc[tarih]
        kapanis  = float(row["kapanis"])
        yuksek   = float(row["yuksek"])
        dusuk    = float(row["dusuk"])
        acilis   = float(row["acilis"])

        dunku_kapanis = float(df.iloc[i - 1]["kapanis"]) if i > 0 else kapanis

        # -- Aktif kutuları kontrol et --
        hala_aktif = []
        for kutu in aktif_kutular:
            if kapanis > kutu["ust"] or kapanis < kutu["alt"]:
                # Kutu kırıldı → kapat
                s = Radar2Sonucu(
                    olay_tarihi=kutu["olay"],
                    kutu_baslangic=kutu["baslangic"],
                    kutu_bitis=tarih,
                    ust_sinir=kutu["ust"],
                    alt_sinir=kutu["alt"],
                    pencere_uzunlugu=(df.index.get_loc(tarih) - df.index.get_loc(kutu["baslangic"])),
                    kirilis_tarihi=tarih,
                )
                sonuclar.append(s)
            else:
                hala_aktif.append(kutu)
        aktif_kutular = hala_aktif

        # -- Yeni olay tespiti --
        if tarih.date() not in anomali_tarihleri:
            continue

        degisim = _gun_degisim(kapanis, dunku_kapanis)

        # Tavan → filtrele
        if degisim >= TAVAN_ESIGI:
            continue

        # Taban veya savaş mumu → çıpala
        taban_mi  = degisim <= TABAN_ESIGI
        savas_mi  = _savas_mumu_mu(row)

        if not (taban_mi or savas_mi):
            continue

        ust = dunku_kapanis
        alt = dusuk

        aktif_kutular.append({
            "olay":      tarih,
            "baslangic": tarih,
            "ust":       ust,
            "alt":       alt,
        })

    # Veri bittiğinde hâlâ açık kutular — son bilinen güne kapat
    son_tarih = tarihler[-1] if tarihler else None
    for kutu in aktif_kutular:
        s = Radar2Sonucu(
            olay_tarihi=kutu["olay"],
            kutu_baslangic=kutu["baslangic"],
            kutu_bitis=son_tarih,
            ust_sinir=kutu["ust"],
            alt_sinir=kutu["alt"],
            pencere_uzunlugu=(df.index.get_loc(son_tarih) - df.index.get_loc(kutu["baslangic"])) + 1 if son_tarih else 0,
            kirilis_tarihi=None,
        )
        sonuclar.append(s)

    return sonuclar
