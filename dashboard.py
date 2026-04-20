import streamlit as st
import psycopg2
import pandas as pd
from streamlit_lightweight_charts import renderLightweightCharts

st.set_page_config(
    page_title="Minerva — Anomali Tespiti",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    .stApp {
        background-color: #0a0a0f;
        color: #e0e0e0;
    }

    /* Üst bar */
    .minerva-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 20px 0 16px 0;
        border-bottom: 1px solid #1e1e2e;
        margin-bottom: 24px;
    }

    .minerva-logo {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 18px;
        font-weight: 500;
        color: #ffffff;
        letter-spacing: 0.08em;
    }

    .minerva-logo span {
        color: #3b82f6;
    }

    .minerva-badge {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        color: #3b82f6;
        border: 1px solid #1e3a5f;
        padding: 3px 8px;
        border-radius: 2px;
        letter-spacing: 0.1em;
    }

    /* Nav tabs */
    .nav-container {
        display: flex;
        gap: 2px;
        margin-bottom: 28px;
        border-bottom: 1px solid #1e1e2e;
    }

    /* Metrik kartlar */
    .metric-card {
        background: #0f0f1a;
        border: 1px solid #1e1e2e;
        border-radius: 4px;
        padding: 16px 20px;
    }

    .metric-label {
        font-size: 10px;
        font-weight: 500;
        color: #666680;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }

    .metric-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 28px;
        font-weight: 500;
        color: #ffffff;
    }

    .metric-value.warn { color: #f59e0b; }
    .metric-value.danger { color: #ef4444; }
    .metric-value.ok { color: #10b981; }

    /* Anomali tablosu */
    .anomali-row {
        display: grid;
        grid-template-columns: 120px 140px 100px 80px 1fr;
        gap: 16px;
        padding: 12px 16px;
        border-bottom: 1px solid #1a1a2a;
        font-size: 13px;
        align-items: center;
    }

    .anomali-row:hover {
        background: #0f0f1a;
    }

    .anomali-header {
        font-size: 10px;
        font-weight: 500;
        color: #666680;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    .badge-beklemede {
        display: inline-block;
        padding: 2px 8px;
        background: #1c1c00;
        color: #f59e0b;
        border: 1px solid #3d3000;
        border-radius: 2px;
        font-size: 11px;
        font-family: 'IBM Plex Mono', monospace;
    }

    .badge-onaylandi {
        display: inline-block;
        padding: 2px 8px;
        background: #1c0000;
        color: #ef4444;
        border: 1px solid #3d0000;
        border-radius: 2px;
        font-size: 11px;
        font-family: 'IBM Plex Mono', monospace;
    }

    .badge-ret {
        display: inline-block;
        padding: 2px 8px;
        background: #001c08;
        color: #10b981;
        border: 1px solid #003018;
        border-radius: 2px;
        font-size: 11px;
        font-family: 'IBM Plex Mono', monospace;
    }

    .skor-deger {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        color: #a0a0c0;
    }

    /* Sayfa başlıkları */
    .page-title {
        font-size: 13px;
        font-weight: 500;
        color: #666680;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 20px;
        padding-bottom: 8px;
        border-bottom: 1px solid #1e1e2e;
    }

    /* Hisse seçici */
    .stSelectbox label {
        font-size: 10px !important;
        color: #666680 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
    }

    div[data-baseweb="select"] {
        background: #0f0f1a !important;
        border: 1px solid #1e1e2e !important;
        border-radius: 4px !important;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background: #0f0f1a !important;
        border: 1px solid #1e1e2e !important;
        border-radius: 4px !important;
        font-size: 12px !important;
        font-family: 'IBM Plex Mono', monospace !important;
    }

    /* Butonlar */
    .stButton button {
        background: #0f0f1a !important;
        border: 1px solid #1e1e2e !important;
        color: #a0a0c0 !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 11px !important;
        letter-spacing: 0.08em !important;
        border-radius: 2px !important;
        padding: 6px 16px !important;
    }

    .stButton button:hover {
        border-color: #3b82f6 !important;
        color: #3b82f6 !important;
    }

    /* Sidebar gizle */
    section[data-testid="stSidebar"] { display: none; }
    .css-18e3th9 { padding-top: 0 !important; }

    /* Textarea */
    .stTextArea textarea {
        background: #0f0f1a !important;
        border: 1px solid #1e1e2e !important;
        color: #e0e0e0 !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 12px !important;
    }

    /* Dataframe gizle, kendi tablomuz var */
    .feature-section {
        margin-bottom: 32px;
    }

    .feature-section-title {
        font-size: 10px;
        font-weight: 600;
        color: #3b82f6;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-bottom: 12px;
        margin-top: 24px;
    }

    .divider {
        border: none;
        border-top: 1px solid #1e1e2e;
        margin: 24px 0;
    }
</style>
""", unsafe_allow_html=True)

# DB bağlantısı
DB_CONFIG = {
    "host": st.secrets["DB_HOST"],
    "port": int(st.secrets["DB_PORT"]),
    "database": st.secrets["DB_NAME"],
    "user": st.secrets["DB_USER"],
    "password": st.secrets["DB_PASSWORD"]
}

@st.cache_resource
def baglanti():
    return psycopg2.connect(**DB_CONFIG)

conn = baglanti()

# Header
st.markdown("""
<div class="minerva-header">
    <div class="minerva-logo">MINERVA<span>.</span>BIST</div>
    <div class="minerva-badge">FAZ A — ANOMALİ TESPİTİ</div>
</div>
""", unsafe_allow_html=True)

# Üst kontroller
col_hisse, col_sayfa = st.columns([2, 8])

with col_hisse:
    hisseler = pd.read_sql(
        "SELECT DISTINCT hisse_kodu FROM hisse_fiyatlari ORDER BY hisse_kodu", conn
    )
    secilen = st.selectbox("Hisse", hisseler["hisse_kodu"].tolist(), label_visibility="collapsed")

with col_sayfa:
    sayfa = st.radio(
        "Sayfa",
        ["Fiyat Grafiği", "Anomali Kayıtları", "Değerlendirme", "Feature Analizi"],
        horizontal=True,
        label_visibility="collapsed"
    )

st.markdown("<hr style='border:none;border-top:1px solid #1e1e2e;margin:0 0 24px 0'>", unsafe_allow_html=True)

# ─── FİYAT GRAFİĞİ ───────────────────────────────────────────
if sayfa == "Fiyat Grafiği":
    st.markdown(f'<div class="page-title">{secilen} — Fiyat Grafiği</div>', unsafe_allow_html=True)

    df = pd.read_sql("""
        SELECT zaman, acilis, kapanis, yuksek, dusuk, hacim
        FROM hisse_fiyatlari
        WHERE hisse_kodu = %s
        ORDER BY zaman
    """, conn, params=(secilen,))

    anomaliler = pd.read_sql("""
        SELECT baslangic_zaman, skor, durum
        FROM anomali_kayitlari
        WHERE hisse_kodu = %s
    """, conn, params=(secilen,))

    if not df.empty:
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

        candle_data = df[["time","acilis","yuksek","dusuk","kapanis"]].rename(columns={
            "acilis":"open","yuksek":"high","dusuk":"low","kapanis":"close"
        }).to_dict("records")

        hacim_data = df[["time","hacim"]].rename(columns={"hacim":"value"}).to_dict("records")

        markers = []
        if not anomaliler.empty:
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

        renderLightweightCharts([{
            "chart": {
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
            },
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
                {
                    "type": "Histogram",
                    "data": hacim_data,
                    "options": {
                        "color": "#1e2a3a",
                        "priceFormat": {"type": "volume"},
                        "priceScaleId": "volume"
                    }
                }
            ]
        }], key=f"chart_{secilen}")
    else:
        st.info("Bu hisse için veri bulunamadı.")

# ─── ANOMALİ KAYITLARI ───────────────────────────────────────
elif sayfa == "Anomali Kayıtları":
    st.markdown(f'<div class="page-title">{secilen} — Anomali Kayıtları</div>', unsafe_allow_html=True)

    anomaliler = pd.read_sql("""
        SELECT id, tespit_zamani, anomali_tipi,
               ROUND(skor::numeric, 4) as skor,
               baslangic_zaman, durum, notlar
        FROM anomali_kayitlari
        WHERE hisse_kodu = %s
        ORDER BY skor ASC
    """, conn, params=(secilen,))

    if anomaliler.empty:
        st.info("Kayıt bulunamadı.")
    else:
        toplam = len(anomaliler)
        beklemede = len(anomaliler[anomaliler["durum"] == "beklemede"])
        onaylandi = len(anomaliler[anomaliler["durum"] == "🔴 onaylandi"])
        ret = len(anomaliler[anomaliler["durum"] == "🟢 ret"])

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Toplam Anomali</div>
                <div class="metric-value">{toplam}</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Beklemede</div>
                <div class="metric-value warn">{beklemede}</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Onaylandı</div>
                <div class="metric-value danger">{onaylandi}</div>
            </div>""", unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Reddedildi</div>
                <div class="metric-value ok">{ret}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Tablo başlığı
        st.markdown("""
        <div class="anomali-row anomali-header">
            <span>Tarih</span>
            <span>Tespit Zamanı</span>
            <span>Tip</span>
            <span>Skor</span>
            <span>Durum</span>
        </div>""", unsafe_allow_html=True)

        for _, row in anomaliler.iterrows():
            tarih = str(row["baslangic_zaman"])[:10]
            tespit = str(row["tespit_zamani"])[:16].replace("T", " ")
            tip = row["anomali_tipi"].replace("_", " ").upper()
            skor = f"{row['skor']:.4f}"
            durum = row["durum"]

            if "onaylandi" in durum:
                badge = f'<span class="badge-onaylandi">ONAYLANDI</span>'
            elif "ret" in durum:
                badge = f'<span class="badge-ret">REDDEDİLDİ</span>'
            else:
                badge = f'<span class="badge-beklemede">BEKLEMEDE</span>'

            st.markdown(f"""
            <div class="anomali-row">
                <span style="font-family:'IBM Plex Mono',monospace;font-size:12px">{tarih}</span>
                <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#666680">{tespit}</span>
                <span style="font-size:11px;color:#a0a0c0">{tip}</span>
                <span class="skor-deger">{skor}</span>
                <span>{badge}</span>
            </div>""", unsafe_allow_html=True)

# ─── DEĞERLENDİRME ───────────────────────────────────────────
elif sayfa == "Değerlendirme":
    st.markdown(f'<div class="page-title">{secilen} — Anomali Değerlendirme</div>', unsafe_allow_html=True)

    anomaliler = pd.read_sql("""
        SELECT id, baslangic_zaman, skor, durum, notlar
        FROM anomali_kayitlari
        WHERE hisse_kodu = %s
        ORDER BY skor ASC
    """, conn, params=(secilen,))

    if anomaliler.empty:
        st.info("Değerlendirilecek anomali yok.")
    else:
        for _, satir in anomaliler.iterrows():
            tarih = str(satir["baslangic_zaman"])[:10]
            skor = round(satir["skor"], 4)
            durum = satir["durum"]

            with st.expander(f"{tarih}   |   Skor: {skor}   |   {durum}"):
                df_detay = pd.read_sql("""
                    SELECT zaman, acilis, kapanis, yuksek, dusuk
                    FROM hisse_fiyatlari
                    WHERE hisse_kodu = %s
                    AND zaman BETWEEN %s::timestamptz - interval '15 days'
                               AND %s::timestamptz + interval '15 days'
                    ORDER BY zaman
                """, conn, params=(secilen, satir["baslangic_zaman"], satir["baslangic_zaman"]))

                if not df_detay.empty:
                    df_detay["zaman"] = pd.to_datetime(df_detay["zaman"]).dt.tz_localize(None)
                    df_detay["tarih"] = df_detay["zaman"].dt.date
                    df_detay = df_detay.groupby("tarih").agg(
                        acilis=("acilis","first"), yuksek=("yuksek","max"),
                        dusuk=("dusuk","min"), kapanis=("kapanis","last")
                    ).reset_index()
                    df_detay["time"] = df_detay["tarih"].astype(str)

                    detay_data = df_detay[["time","acilis","yuksek","dusuk","kapanis"]].rename(columns={
                        "acilis":"open","yuksek":"high","dusuk":"low","kapanis":"close"
                    }).to_dict("records")

                    renderLightweightCharts([{
                        "chart": {
                            "layout": {
                                "background": {"type":"solid","color":"#0a0a0f"},
                                "textColor":"#666680","fontSize":10,
                                "fontFamily":"IBM Plex Mono"
                            },
                            "grid": {"vertLines":{"color":"#111120"},"horzLines":{"color":"#111120"}},
                            "height": 220,
                            "timeScale": {"borderColor":"#1e1e2e"},
                            "rightPriceScale": {"borderColor":"#1e1e2e"}
                        },
                        "series": [{
                            "type": "Candlestick",
                            "data": detay_data,
                            "options": {
                                "upColor":"#10b981","downColor":"#ef4444",
                                "borderVisible":False,
                                "wickUpColor":"#10b981","wickDownColor":"#ef4444"
                            }
                        }]
                    }], key=f"detay_{satir['id']}")

                not_metni = st.text_area(
                    "Değerlendirme notu",
                    value=satir["notlar"] if satir["notlar"] else "",
                    key=f"not_{satir['id']}",
                    height=80
                )

                c1, c2, c3 = st.columns([1,1,4])
                if c1.button("Onayla", key=f"onayla_{satir['id']}"):
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE anomali_kayitlari SET durum='🔴 onaylandi', notlar=%s WHERE id=%s",
                        (not_metni, satir["id"])
                    )
                    conn.commit(); cur.close()
                    st.success("Onaylandı."); st.rerun()

                if c2.button("Reddet", key=f"reddet_{satir['id']}"):
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE anomali_kayitlari SET durum='🟢 ret', notlar=%s WHERE id=%s",
                        (not_metni, satir["id"])
                    )
                    conn.commit(); cur.close()
                    st.success("Reddedildi."); st.rerun()

# ─── FEATURE ANALİZİ ─────────────────────────────────────────
elif sayfa == "Feature Analizi":
    st.markdown(f'<div class="page-title">{secilen} — Feature Analizi</div>', unsafe_allow_html=True)

    feature_df = pd.read_sql("""
        SELECT tarih,
               fiyat_degisimi_5g, fiyat_degisimi_20g, fiyat_degisimi_60g,
               volatilite_5g, volatilite_20g, volatilite_60g,
               rvol_5g, rvol_20g,
               fiyat_bant_genisligi_5g, fiyat_bant_genisligi_20g
        FROM feature_cache
        WHERE hisse_kodu = %s
        ORDER BY tarih DESC
        LIMIT 60
    """, conn, params=(secilen,))

    if feature_df.empty:
        st.info("Feature verisi bulunamadı.")
    else:
        feature_df["tarih"] = pd.to_datetime(feature_df["tarih"])
        feature_df = feature_df.sort_values("tarih")
        son = feature_df.iloc[-1]

        # RVOL
        st.markdown('<div class="feature-section-title">Goreceli Hacim — RVOL</div>', unsafe_allow_html=True)
        st.caption("1.0 = normal hacim seviyesi")
        c1, c2 = st.columns(2)
        rvol5 = son["rvol_5g"]
        rvol20 = son["rvol_20g"]
        renk5 = "danger" if rvol5 > 2 else ("warn" if rvol5 > 1.5 else "ok")
        renk20 = "danger" if rvol20 > 2 else ("warn" if rvol20 > 1.5 else "ok")
        c1.markdown(f"""<div class="metric-card"><div class="metric-label">RVOL 5G</div>
            <div class="metric-value {renk5}">{rvol5:.2f}x</div></div>""", unsafe_allow_html=True)
        c2.markdown(f"""<div class="metric-card"><div class="metric-label">RVOL 20G</div>
            <div class="metric-value {renk20}">{rvol20:.2f}x</div></div>""", unsafe_allow_html=True)
        st.line_chart(feature_df.set_index("tarih")[["rvol_5g","rvol_20g"]])

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # Volatilite
        st.markdown('<div class="feature-section-title">Volatilite</div>', unsafe_allow_html=True)
        st.caption("Gunluk fiyat degisiminin standart sapması")
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"""<div class="metric-card"><div class="metric-label">VOL 5G</div>
            <div class="metric-value">{son['volatilite_5g']:.4f}</div></div>""", unsafe_allow_html=True)
        c2.markdown(f"""<div class="metric-card"><div class="metric-label">VOL 20G</div>
            <div class="metric-value">{son['volatilite_20g']:.4f}</div></div>""", unsafe_allow_html=True)
        c3.markdown(f"""<div class="metric-card"><div class="metric-label">VOL 60G</div>
            <div class="metric-value">{son['volatilite_60g']:.4f}</div></div>""", unsafe_allow_html=True)
        st.line_chart(feature_df.set_index("tarih")[["volatilite_5g","volatilite_20g","volatilite_60g"]])

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # Fiyat değişimi
        st.markdown('<div class="feature-section-title">Kumulatif Fiyat Degisimi</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        for col, key, label in [(c1,"fiyat_degisimi_5g","5 GUNLUK"),
                                  (c2,"fiyat_degisimi_20g","20 GUNLUK"),
                                  (c3,"fiyat_degisimi_60g","60 GUNLUK")]:
            val = son[key] * 100
            renk = "danger" if val < -5 else ("ok" if val > 5 else "warn")
            col.markdown(f"""<div class="metric-card"><div class="metric-label">{label}</div>
                <div class="metric-value {renk}">{val:+.2f}%</div></div>""", unsafe_allow_html=True)

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # Bant genişliği
        st.markdown('<div class="feature-section-title">Fiyat Bant Genisligi</div>', unsafe_allow_html=True)
        st.caption("Daralma = sıkışma sinyali olabilir")
        st.line_chart(feature_df.set_index("tarih")[["fiyat_bant_genisligi_5g","fiyat_bant_genisligi_20g"]])