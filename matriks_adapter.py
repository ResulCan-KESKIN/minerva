import pandas as pd
import requests

class MatriksAdapter:
    """
    Matriks API üzerinden veri çeker.
    Matriks'e geçince bu dosyayı doldur,
    veri_cek.py içinde sadece şunu değiştir:
    
    from yahoo_adapter import YahooAdapter as Adapter
        →
    from matriks_adapter import MatriksAdapter as Adapter
    """

    def __init__(self, api_key=None, base_url=None):
        """
        api_key  : Matriks API anahtarın
        base_url : Matriks REST API adresi
        """
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def gunluk_ohlcv(self, hisse_kodu, baslangic=None, bitis=None):
        """
        Günlük OHLCV verisi.
        
        Döndüreceği DataFrame sütunları (Yahoo ile aynı):
        zaman, acilis, yuksek, dusuk, kapanis, hacim
        
        TODO: Matriks endpoint ve parametre adlarını buraya yaz.
        Örnek:
            GET /api/v1/bars?symbol=THYAO&from=2024-01-01&to=2026-01-01&period=1d
        """
        # TODO: Matriks'e geçince doldur
        # response = requests.get(
        #     f"{self.base_url}/bars",
        #     headers=self.headers,
        #     params={
        #         "symbol": hisse_kodu,
        #         "from": baslangic,
        #         "to": bitis,
        #         "period": "1d"
        #     }
        # )
        # data = response.json()
        # df = pd.DataFrame(data)
        # df = df.rename(columns={...})  # Matriks kolon adlarını buraya yaz
        # return df[["zaman", "acilis", "yuksek", "dusuk", "kapanis", "hacim"]]
        return pd.DataFrame()

    def akd_verisi(self, hisse_kodu, baslangic=None, bitis=None):
        """
        Aracı kurum dağılımı (AKD).
        
        Döndüreceği DataFrame sütunları:
        tarih, hisse_kodu, kurum_kodu, net_alim, net_satim, hacim
        
        Bu veri HHI, kurum birikim skoru gibi feature'ların kaynağı.
        
        TODO: Matriks AKD endpoint'ini buraya yaz.
        """
        # TODO: Matriks'e geçince doldur
        return pd.DataFrame()

    def takas_verisi(self, hisse_kodu, baslangic=None, bitis=None):
        """
        Takas verisi.
        
        Döndüreceği DataFrame sütunları:
        tarih, hisse_kodu, kurum_kodu, takas_miktari, yon
        
        TODO: Matriks takas endpoint'ini buraya yaz.
        """
        # TODO: Matriks'e geçince doldur
        return pd.DataFrame()

    def kap_bildirimleri(self, hisse_kodu, baslangic=None, bitis=None):
        """
        KAP bildirimleri.
        
        Döndüreceği DataFrame sütunları:
        bildirim_zamani, hisse_kodu, baslik, icerik, kategori
        
        Bu veri anomali tarihiyle çakışan haberleri bulmak için kullanılır.
        
        TODO: Matriks KAP endpoint'ini buraya yaz.
        """
        # TODO: Matriks'e geçince doldur
        return pd.DataFrame()