"""
CLI: tüm aktif BIST hisseleri için Faz 1-4 tarama.

Çalıştırma: python tarama_calistir.py
"""

import logging
import time
import warnings
warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
from concurrent.futures import ThreadPoolExecutor, as_completed

from db import _yeni_baglanti
from data_access import hisse_listesi_cek, fiyat_verisi_cek, anomali_tarihleri_cek, dolasim_lot_cek
from engine.tarama import hisse_tara

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

MAX_WORKERS = 3
FIYAT_GUN   = 250


def _isle(row) -> tuple[str, int]:
    """Her thread kendi izole bağlantısını açar — paylaşım yok."""
    symbol   = row["symbol"]
    stock_id = int(row["id"])
    conn = None
    try:
        conn = _yeni_baglanti()
        df   = fiyat_verisi_cek(conn, stock_id, gun=FIYAT_GUN)
        if df.empty or len(df) < 10:
            return symbol, 0
        anomaliler  = anomali_tarihleri_cek(conn, symbol)
        dolasim_lot = dolasim_lot_cek(conn, stock_id)
        n = hisse_tara(conn, stock_id, symbol, df, anomaliler, dolasim_lot)
        return symbol, n
    except Exception as e:
        log.error(f"{symbol} hata: {e}")
        return symbol, -1
    finally:
        if conn and not conn.closed:
            conn.close()


def main():
    conn    = _yeni_baglanti()
    hisseler = hisse_listesi_cek(conn)
    conn.close()
    toplam   = len(hisseler)
    log.info(f"{toplam} hisse taranacak")

    basarili = 0
    hata     = 0
    t0       = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        gelecekler = {ex.submit(_isle, row): row["symbol"]
                      for _, row in hisseler.iterrows()}
        for i, fut in enumerate(as_completed(gelecekler), 1):
            symbol, n = fut.result()
            if n >= 0:
                basarili += 1
                log.info(f"[{i}/{toplam}] {symbol}: {n} kayıt")
            else:
                hata += 1

    gecen = time.time() - t0
    log.info(f"Tamamlandı — {basarili} başarılı, {hata} hatalı, {gecen:.1f}s")


if __name__ == "__main__":
    main()
