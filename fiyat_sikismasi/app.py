import streamlit as st
import pandas as pd
from db import get_conn
from data_access import ozet_metrikler_cek
from pages import genel_bakis, hisse_detay

st.set_page_config(
    page_title="Minerva — Fiyat Sıkışması",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'IBM Plex Mono', monospace !important;
    background-color: #0c0c13 !important;
    color: #c0c0d0;
}
.stApp { background-color: #0c0c13 !important; }
.block-container { padding-top: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { display: none !important; }
div[data-testid="stToolbar"]     { display: none !important; }
header[data-testid="stHeader"]   { display: none !important; }
footer { display: none !important; }

div[data-testid="stRadio"] > label { display: none !important; }
div[data-testid="stRadio"] > div {
    display: flex !important; flex-direction: row !important;
    gap: 0 !important; flex-wrap: nowrap !important;
    border-bottom: 1px solid #1a1a24 !important;
    padding: 0 !important; margin: 0 !important;
    background: transparent !important;
}
div[data-testid="stRadio"] label {
    display: flex !important; align-items: center !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important; color: #3a3a55 !important;
    letter-spacing: 0.1em !important; text-transform: uppercase !important;
    padding: 9px 16px 10px !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px !important; cursor: pointer !important;
    white-space: nowrap !important; background: transparent !important;
    transition: color 0.1s !important;
}
div[data-testid="stRadio"] label:hover { color: #8888a8 !important; }
div[data-testid="stRadio"] label:has(input:checked) {
    color: #e0e0f0 !important;
    border-bottom: 2px solid #4d8ef0 !important;
}
div[data-testid="stRadio"] label > div:first-child { display: none !important; }
div[data-testid="stRadio"] label > p { margin: 0 !important; }

.stButton > button {
    background: transparent !important; border: 1px solid #1e1e30 !important;
    color: #4a4a68 !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important; letter-spacing: 0.1em !important;
    text-transform: uppercase !important; border-radius: 2px !important;
    padding: 4px 12px !important;
}
.stButton > button:hover {
    border-color: #4d8ef0 !important; color: #4d8ef0 !important;
    background: #0d1a2e !important;
}

div[data-baseweb="select"] > div {
    background: #0c0c13 !important; border: 1px solid #1e1e30 !important;
    border-radius: 2px !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important; color: #8888a8 !important; min-height: 32px !important;
}
div[data-baseweb="select"] svg { color: #3a3a55 !important; }
[data-baseweb="popover"] { background: #12121e !important; border: 1px solid #1e1e30 !important; }
[role="option"] {
    background: #12121e !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important; color: #8888a8 !important;
}
[role="option"]:hover { background: #1a1a2e !important; color: #e0e0f0 !important; }
[aria-selected="true"] { background: #1a1a2e !important; color: #4d8ef0 !important; }

::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: #0c0c13; }
::-webkit-scrollbar-thumb { background: #1e1e30; border-radius: 1px; }
::-webkit-scrollbar-thumb:hover { background: #2e2e44; }

div[data-testid="stVerticalBlock"] > div { padding-top: 0 !important; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def _header_stats():
    conn = get_conn()
    return ozet_metrikler_cek(conn)


try:
    s = _header_stats()
    hisse_n   = int(s.get("hisse_sayisi", 0))
    toplam_n  = int(s.get("toplam_sikisma", 0))
    son_gunc  = s.get("son_guncelleme")
    son_str   = str(son_gunc)[:10] if son_gunc else "—"
except Exception:
    hisse_n = toplam_n = 0
    son_str = "—"

# Header
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:10px 0 0 0">
  <div style="display:flex;align-items:center;gap:10px">
    <div style="width:22px;height:22px;border-radius:50%;background:#4d8ef0;
                display:flex;align-items:center;justify-content:center;
                font-size:11px;font-weight:500;color:#fff;flex-shrink:0">M</div>
    <span style="font-size:13px;font-weight:500;color:#e0e0f0;letter-spacing:0.04em">Minerva</span>
    <span style="color:#1e1e30;font-size:13px">·</span>
    <span style="font-size:11px;color:#3a3a55;letter-spacing:0.06em">FAZ B</span>
    <span style="color:#1e1e30;font-size:11px">·</span>
    <span style="font-size:11px;color:#3a3a55;letter-spacing:0.06em">FİYAT SIKIŞ MASI</span>
  </div>
  <div style="display:flex;align-items:center;gap:16px">
    <span style="font-size:10px;color:#3a3a55;letter-spacing:0.06em">
      piyasa <span style="color:#6a6a88">BIST</span>
    </span>
    <span style="font-size:10px;color:#3a3a55">·</span>
    <span style="font-size:10px;color:#3a3a55;letter-spacing:0.06em">
      son güncelleme <span style="color:#6a6a88">{son_str}</span>
    </span>
    <span style="font-size:10px;color:#3a3a55">·</span>
    <span style="font-size:10px;color:#22c55e;letter-spacing:0.06em">● ready</span>
  </div>
</div>
""", unsafe_allow_html=True)

# Navigation + hisse seçici
col_nav, col_hisse = st.columns([8, 2])

with col_nav:
    sayfa = st.radio(
        "nav",
        ["Genel Bakis", "Hisse Detay"],
        horizontal=True,
        label_visibility="collapsed",
        key="nav_sayfa",
    )

conn = get_conn()
with col_hisse:
    hisseler = pd.read_sql(
        "SELECT symbol FROM stocks WHERE is_active = true ORDER BY symbol", conn
    )
    secilen = st.selectbox(
        "hisse", hisseler["symbol"].tolist(),
        label_visibility="collapsed",
        key="nav_hisse",
    )

# Status bar
st.markdown(f"""
<div style="font-size:10px;color:#2e2e48;letter-spacing:0.06em;
            padding:5px 0 12px 0;border-bottom:1px solid #12121e;
            display:flex;justify-content:space-between">
  <span>
    takip <span style="color:#4a4a68">{hisse_n}</span> hisse
    &nbsp;·&nbsp; toplam sıkışma <span style="color:#4a4a68">{toplam_n:,}</span>
    &nbsp;·&nbsp; kaynak <span style="color:#4a4a68">stock_prices · anomali_kayitlari</span>
  </span>
  <span style="color:#2e2e48">ticker — {secilen}</span>
</div>
""", unsafe_allow_html=True)

# Page routing
if sayfa == "Genel Bakis":
    genel_bakis.goster()
elif sayfa == "Hisse Detay":
    hisse_detay.goster(secilen)

# Footer
st.markdown("""
<div style="margin-top:40px;padding:8px 0;border-top:1px solid #12121e;
            display:flex;justify-content:space-between;align-items:center">
  <span style="font-size:10px;color:#2a2a40;letter-spacing:0.06em">
    <span style="color:#22c55e">●</span>
    &nbsp;fiyat sıkışması — radar1 · radar2 · faz 2-3-4
  </span>
  <span style="font-size:10px;color:#2a2a40;letter-spacing:0.06em">
    Minerva FAZ B
  </span>
</div>
""", unsafe_allow_html=True)
