import pandas as pd
from streamlit_lightweight_charts import renderLightweightCharts

CHART_STYLE = {
    "layout": {
        "background": {"type": "solid", "color": "#0a0a0f"},
        "textColor": "#666680",
        "fontSize": 11,
        "fontFamily": "IBM Plex Mono"
    },
    "grid": {
        "vertLines": {"color": "#111120"},
        "horzLines": {"color": "#111120"}
    },
    "crosshair": {"mode": 1},
    "timeScale": {"borderColor": "#1e1e2e"},
    "rightPriceScale": {"borderColor": "#1e1e2e"}
}

def hazirla_gunluk(df):
    df["zaman"] = pd.to_datetime(df["zaman"]).dt.tz_localize(None)
    df["tarih"] = df["zaman"].dt.date
    df = df.groupby("tarih").agg(
        acilis=("acilis", "first"),
        yuksek=("yuksek", "max"),
        dusuk=("dusuk", "min"),
        kapanis=("kapanis", "last"),
        hacim=("hacim", "sum")
    ).reset_index()
    df["time"] = df["tarih"].astype(str)
    return df

def candlestick_goster(df, anomaliler=None, key="grafik", yukseklik=450):
    df = hazirla_gunluk(df)

    candle_data = df[["time","acilis","yuksek","dusuk","kapanis"]].rename(columns={
        "acilis":"open","yuksek":"high","dusuk":"low","kapanis":"close"
    }).to_dict("records")

    hacim_data = df[["time","hacim"]].rename(columns={"hacim":"value"}).to_dict("records")

    markers = []
    if anomaliler is not None and not anomaliler.empty:
        anomaliler["tarih"] = pd.to_datetime(
            anomaliler["baslangic_zaman"]
        ).dt.tz_localize(None).dt.date.astype(str)
        for _, row in anomaliler.iterrows():
            markers.append({
                "time": row["tarih"],
                "position": "aboveBar",
                "color": "#ef4444",
                "shape": "arrowDown",
                "text": "A"
            })

    chart = dict(CHART_STYLE)
    chart["height"] = yukseklik
    chart["leftPriceScale"] = {"visible": False}
    chart["rightPriceScale"] = {"scaleMargins": {"top": 0.1, "bottom": 0.2}}

    renderLightweightCharts([{
        "chart": chart,
        "series": [
            {
                "type": "Candlestick",
                "data": candle_data,
                "markers": markers,
                "options": {
                    "upColor": "#10b981",
                    "downColor": "#ef4444",
                    "borderVisible": False,
                    "wickUpColor": "#10b981",
                    "wickDownColor": "#ef4444"
                }
            },
            
        ]
    }], key=key)