import pandas as pd
from streamlit_lightweight_charts import renderLightweightCharts

CHART_BG   = "#0c0c13"
GRID_COLOR = "#0f0f18"
BORDER_COL = "#1a1a24"
TEXT_COLOR = "#3a3a55"

RADAR_RENK = {
    "radar1": "#4d8ef0",
    "radar2": "#d4820a",
}


def _hazirla(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["price_date"] = pd.to_datetime(df["price_date"])
    df = df.sort_values("price_date")
    df["time"] = df["price_date"].dt.strftime("%Y-%m-%d")
    return df


def grafik_kutu_goster(
    df: pd.DataFrame,
    kutular: list,
    anomali_tarihleri=None,
    key: str = "grafik_kutu",
    yukseklik: int = 420,
):
    df = _hazirla(df)
    anomali_set = {str(t) for t in (anomali_tarihleri or set())}

    candle_data = df[["time", "acilis", "yuksek", "dusuk", "kapanis"]].rename(
        columns={"acilis": "open", "yuksek": "high", "dusuk": "low", "kapanis": "close"}
    ).to_dict("records")

    volume_data = [
        {
            "time":  row["time"],
            "value": float(row["hacim"]),
            "color": "#d4820a44" if row["time"] in anomali_set else "#1e1e3044",
        }
        for _, row in df.iterrows()
    ]

    kutu_markers = []
    for k in kutular:
        bas = str(k["baslangic"])
        bit = str(k["bitis"])
        renk = RADAR_RENK.get(k.get("radar", "radar1"), "#4d8ef0")
        kutu_markers.append({"time": bas, "position": "belowBar", "color": renk,
                              "shape": "arrowUp", "text": k.get("radar", "").upper()})
        kutu_markers.append({"time": bit, "position": "aboveBar", "color": renk,
                              "shape": "arrowDown", "text": f'{k.get("zirve", 0):.2f}'})

    chart_cfg = {
        "layout": {
            "background": {"type": "solid", "color": CHART_BG},
            "textColor": TEXT_COLOR,
            "fontSize": 10,
            "fontFamily": "IBM Plex Mono",
        },
        "grid": {
            "vertLines": {"color": GRID_COLOR},
            "horzLines": {"color": GRID_COLOR},
        },
        "crosshair": {"mode": 1},
        "timeScale":       {"borderColor": BORDER_COL, "barSpacing": 5},
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
                "type": "Candlestick",
                "data": candle_data,
                "markers": kutu_markers,
                "options": {
                    "upColor":       "#22c55e",
                    "downColor":     "#e84040",
                    "borderUpColor": "#22c55e",
                    "borderDownColor": "#e84040",
                    "wickUpColor":   "#22c55e",
                    "wickDownColor": "#e84040",
                    "priceScaleId": "right",
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
