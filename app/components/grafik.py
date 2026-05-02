import pandas as pd
from streamlit_lightweight_charts import renderLightweightCharts

CHART_BG   = "#0c0c13"
GRID_COLOR = "#0f0f18"
BORDER_COL = "#1a1a24"
TEXT_COLOR = "#3a3a55"

TIP_RENK = {
    "anomali_z60":   "#4d8ef0",
    "anomali_z120":  "#06b6d4",
    "anomali_rz60":  "#d4820a",
    "anomali_rz120": "#22c55e",
    "anomali_t":     "#a07af0",
}
TIP_KISA = {
    "anomali_z60": "Z60", "anomali_z120": "Z120",
    "anomali_rz60": "RZ60", "anomali_rz120": "RZ120",
    "anomali_t": "T",
}


def _hazirla(df):
    zaman_kolon = "zaman" if "zaman" in df.columns else "price_date"
    df = df.copy()
    df[zaman_kolon] = pd.to_datetime(df[zaman_kolon]).dt.tz_localize(None)
    df["tarih"] = df[zaman_kolon].dt.date
    df = df.groupby("tarih").agg(
        acilis=("acilis", "first"),
        yuksek=("yuksek", "max"),
        dusuk=("dusuk", "min"),
        kapanis=("kapanis", "last"),
        hacim=("hacim", "sum"),
    ).reset_index()
    df["time"] = df["tarih"].astype(str)
    return df


def candlestick_goster(df, anomaliler=None, key="grafik", yukseklik=380):
    df = _hazirla(df)

    anomali_tarihleri = set()
    markers = []
    if anomaliler is not None and not anomaliler.empty:
        zaman_kolon = "baslangic_zaman" if "baslangic_zaman" in anomaliler.columns else "price_date"
        anoms = anomaliler.copy()
        anoms["tarih"] = pd.to_datetime(anoms[zaman_kolon]).dt.tz_localize(None).dt.date.astype(str)
        for _, row in anoms.iterrows():
            anomali_tarihleri.add(row["tarih"])
            tip  = row.get("anomali_tipi", "")
            skor = row.get("skor", 0)
            renk = TIP_RENK.get(tip, "#666680")
            kisa = TIP_KISA.get(tip, "A")
            markers.append({
                "time":     row["tarih"],
                "position": "aboveBar",
                "color":    renk,
                "shape":    "arrowDown",
                "text":     f"{kisa}·{skor:.2f}" if skor else kisa,
            })

    price_data = df[["time", "kapanis"]].rename(columns={"kapanis": "value"}).to_dict("records")

    volume_data = [
        {
            "time":  row["time"],
            "value": float(row["hacim"]),
            "color": "#d4820a44" if row["time"] in anomali_tarihleri else "#1e1e3044",
        }
        for _, row in df.iterrows()
    ]

    chart_cfg = {
        "layout": {
            "background": {"type": "solid", "color": CHART_BG},
            "textColor":  TEXT_COLOR,
            "fontSize":   10,
            "fontFamily": "IBM Plex Mono",
        },
        "grid": {
            "vertLines": {"color": GRID_COLOR},
            "horzLines": {"color": GRID_COLOR},
        },
        "crosshair": {"mode": 1},
        "timeScale":      {"borderColor": BORDER_COL, "barSpacing": 6},
        "rightPriceScale": {
            "borderColor":  BORDER_COL,
            "scaleMargins": {"top": 0.05, "bottom": 0.22},
        },
        "height": yukseklik,
    }

    renderLightweightCharts([{
        "chart": chart_cfg,
        "series": [
            {
                "type": "Area",
                "data": price_data,
                "markers": markers,
                "options": {
                    "lineColor":    "#e0e0f0",
                    "topColor":     "rgba(224,224,240,0.06)",
                    "bottomColor":  "rgba(224,224,240,0.0)",
                    "lineWidth":    1,
                    "priceScaleId": "right",
                    "crosshairMarkerRadius": 3,
                    "crosshairMarkerBorderColor": "#e0e0f0",
                    "crosshairMarkerBackgroundColor": "#0c0c13",
                },
            },
            {
                "type": "Histogram",
                "data": volume_data,
                "options": {
                    "priceFormat":  {"type": "volume"},
                    "priceScaleId": "vol",
                    "scaleMargins": {"top": 0.82, "bottom": 0},
                },
            },
        ],
    }], key=key)
