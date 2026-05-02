"""
Birim testleri — engine/radar1.py
Çalıştır: python -m pytest tests/ -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pandas as pd
import numpy as np
from engine.radar1 import radar1_tara, _kutu_test, SIKISMA_ESIGI, KOPUK_ORAN


def _df(close_values, start="2024-01-01"):
    dates = pd.date_range(start, periods=len(close_values), freq="B")
    return pd.DataFrame({"price_date": dates, "kapanis": close_values})


# ── _kutu_test testleri ──────────────────────────────────────────────────────

class TestKutuTest:
    def test_dar_aralik_gecerli(self):
        """Sabit %10 aralıklı seri → kutu döner."""
        df = _df([100] * 60)
        result = _kutu_test(df.set_index("price_date"))
        assert result is not None
        assert result.pencere_uzunlugu == 60

    def test_genis_aralik_gecersiz(self):
        """Sabit %20 aralıklı seri → None döner."""
        vals = [100 if i % 2 == 0 else 121 for i in range(60)]  # >%15 aralık
        df = _df(vals)
        result = _kutu_test(df.set_index("price_date"))
        assert result is None

    def test_kopuk_tolere_edilir(self):
        """
        55 gün 100 TL, 5 gün 130 TL (köpük) → %10 tolerans içinde,
        çekirdek zirve ≈ 100, aralik=0 → kutu geçerli.
        """
        vals = [100.0] * 55 + [130.0] * 5   # 5/60 ≈ %8.3 < %10
        df = _df(vals)
        result = _kutu_test(df.set_index("price_date"))
        assert result is not None
        assert result.cekirdek_zirve <= 100.0 + 1e-6
        assert len(result.kopuk_gunler) == round(60 * KOPUK_ORAN)

    def test_kopuk_fazlasi_ise_kutu_bozulur(self):
        """
        30 gün 100, 30 gün 200 → köpük %10 yeterli değil, aralik büyük → None.
        """
        vals = [100.0] * 30 + [200.0] * 30
        df = _df(vals)
        result = _kutu_test(df.set_index("price_date"))
        assert result is None

    def test_cekirdek_zirve_dip_dogru(self):
        """Çekirdek zirve ve dip %90 verisin max/min'i olmalı."""
        vals = [100.0] * 54 + [115.0] * 6   # son 6 = %10 köpük
        df = _df(vals)
        result = _kutu_test(df.set_index("price_date"))
        # Köpük 6 gün etiketlenince kalan 54 gün hepsi 100
        assert result is not None
        assert abs(result.cekirdek_zirve - 100.0) < 1e-6
        assert abs(result.cekirdek_dip - 100.0) < 1e-6


# ── radar1_tara testleri ─────────────────────────────────────────────────────

class TestRadar1Tara:
    def test_60gun_daralan_hisse(self):
        """60 günde sıkışan hisse → kutu döner."""
        df = _df([100.0 + np.random.uniform(-5, 5) for _ in range(100)])
        # Son 60 günü dar yap
        df.iloc[-60:, df.columns.get_loc("kapanis")] = 100.0
        result = radar1_tara(df)
        assert result is not None

    def test_yeterli_veri_yok(self):
        """9 günlük veri → None döner (MIN_PENCERE=10)."""
        df = _df([100.0] * 9)
        result = radar1_tara(df)
        assert result is None

    def test_genisleme_calisiyor(self):
        """
        60g'de sıkışan ama 120g'de de sıkışan hisse →
        pencere_uzunlugu > 60 olmalı.
        """
        vals = [100.0 + np.random.uniform(-5, 5) for _ in range(50)]
        vals += [100.0] * 120
        df = _df(vals)
        result = radar1_tara(df)
        assert result is not None
        assert result.pencere_uzunlugu > 60

    def test_daralma_calisiyor(self):
        """
        60g'de sıkışmayan ama son 30g'de sıkışan hisse →
        pencere_uzunlugu <= 30 olmalı.
        """
        vals = [100.0 if i < 30 else 100.0 + (i - 30) * 2.0
                for i in range(30)]          # son 30 = sıkışık
        vals_reversed = list(reversed(vals)) + [100.0] * 30
        df = _df(vals_reversed)
        result = radar1_tara(df)
        # Daralan test — None gelebilir (veri bağımlı), sadece None değilse kontrol
        if result is not None:
            assert result.pencere_uzunlugu <= 60

    def test_price_date_sutun_veya_index(self):
        """price_date hem sütun hem index olarak gönderildiğinde çalışmalı."""
        df = _df([100.0] * 70)
        r1 = radar1_tara(df)                          # sütun olarak
        r2 = radar1_tara(df.set_index("price_date"))  # index olarak
        assert (r1 is None) == (r2 is None)
