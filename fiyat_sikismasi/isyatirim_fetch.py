"""
İş Yatırım'dan hisse başına dolaşımdaki lot (ödenmiş sermaye / nominal değer) çeker
ve stocks.dolasim_lot sütununu günceller.

Çalıştırma: python isyatirim_fetch.py
"""

import re
import time
import logging
import requests
import pandas as pd
from db import get_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# İş Yatırım temel veri endpoint'i
ISYATIRIM_URL = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/sirket-karti.aspx"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9",
}

# Fallback: hisse.io JSON API (BIST için public)
HISSEIO_URL = "https://financials.hisseio.com/api/v1/stock/{symbol}/fundamentals"


def _isyatirim_lot(symbol: str) -> float | None:
    """İş Yatırım'dan dolaşım lotunu çekmeye çalış."""
    try:
        params = {"hisse": symbol}
        r = requests.get(ISYATIRIM_URL, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()

        # "Dolaşımdaki Hisse" veya "Ödenmiş Sermaye" satırını ara
        # İş Yatırım sayfası JS-render olduğundan JSON embed'e bak
        text = r.text

        # Embedded JSON pattern: "paidCapital":1234567890
        match = re.search(r'"paidCapital"\s*:\s*([\d.]+)', text)
        if match:
            # Ödenmiş sermaye TL cinsinden, nominal değer 1 TL → lot sayısı
            return float(match.group(1))

        # Alternatif pattern
        match = re.search(r'Ödenmiş Sermaye.*?([\d.,]+)\s*(?:TL|Bin TL|Milyon TL)', text)
        if match:
            val_str = match.group(1).replace(".", "").replace(",", ".")
            val = float(val_str)
            # "Bin TL" ise 1000 çarp, "Milyon TL" ise 1_000_000 çarp
            if "Milyon" in match.group(0):
                val *= 1_000_000
            elif "Bin" in match.group(0):
                val *= 1_000
            return val

    except Exception as e:
        log.debug(f"{symbol} isyatirim fetch hata: {e}")
    return None


def _hisseio_lot(symbol: str) -> float | None:
    """Fallback: hisse.io fundamentals."""
    try:
        url = HISSEIO_URL.format(symbol=symbol)
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        # Alan adı değişebilir — yaygın isimler
        for key in ("paidCapital", "paid_capital", "shares_outstanding", "dolasimLot"):
            if key in data:
                return float(data[key])
    except Exception as e:
        log.debug(f"{symbol} hisseio fetch hata: {e}")
    return None


def lot_guncelle(symbol: str) -> float | None:
    lot = _isyatirim_lot(symbol)
    if lot is None:
        lot = _hisseio_lot(symbol)
    return lot


def tumunu_guncelle():
    conn = get_conn()
    cur = conn.cursor()

    hisseler = pd.read_sql(
        "SELECT id, symbol FROM stocks WHERE is_active = true ORDER BY symbol", conn
    )
    log.info(f"{len(hisseler)} hisse güncellenecek")

    guncellenen = 0
    hata = 0
    for _, row in hisseler.iterrows():
        symbol = row["symbol"]
        stock_id = row["id"]
        lot = lot_guncelle(symbol)
        if lot is not None and lot > 0:
            cur.execute(
                "UPDATE stocks SET dolasim_lot = %s WHERE id = %s",
                (lot, stock_id),
            )
            guncellenen += 1
            log.info(f"{symbol}: {lot:,.0f} lot")
        else:
            hata += 1
            log.warning(f"{symbol}: lot verisi alınamadı")
        time.sleep(0.3)  # rate-limit

    conn.commit()
    cur.close()
    log.info(f"Tamamlandı: {guncellenen} güncellendi, {hata} başarısız")


if __name__ == "__main__":
    tumunu_guncelle()
