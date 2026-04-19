import yfinance as yf
import pandas as pd

class YahooAdapter:
    """
    Yahoo Finance üzerinden veri çeker.
    Matriks'e geçince bu dosyaya dokunulmaz,
    veri_cek.py içinde sadece import değişir.
    """

    def gunluk_ohlcv(self, hisse_kodu, period="2y"):
        """
        Günlük OHLCV verisi çeker.
        
        Döndürdüğü DataFrame sütunları:
        zaman, acilis, yuksek, dusuk, kapanis, hacim
        """
        hisse = yf.Ticker(hisse_kodu)
        df = hisse.history(period=period, interval="1d")

        if df.empty:
            print(f"{hisse_kodu}: Veri gelmedi.")
            return pd.DataFrame()

        df = df.reset_index()
        df = df.rename(columns={
            "Date": "zaman",
            "Open": "acilis",
            "High": "yuksek",
            "Low": "dusuk",
            "Close": "kapanis",
            "Volume": "hacim"
        })
        df["zaman"] = pd.to_datetime(df["zaman"]).dt.tz_localize(None)
        return df[["zaman", "acilis", "yuksek", "dusuk", "kapanis", "hacim"]]

    def akd_verisi(self, hisse_kodu, baslangic=None, bitis=None):
        """
        Aracı kurum dağılımı — Yahoo'da yok.
        Matriks adapter'da dolu olacak.
        """
        return pd.DataFrame()

    def takas_verisi(self, hisse_kodu, baslangic=None, bitis=None):
        """
        Takas verisi — Yahoo'da yok.
        Matriks adapter'da dolu olacak.
        """
        return pd.DataFrame()

    def kap_bildirimleri(self, hisse_kodu, baslangic=None, bitis=None):
        """
        KAP bildirimleri — Yahoo'da yok.
        Matriks adapter'da dolu olacak.
        """
        return pd.DataFrame()