# app.py
import streamlit as st
import pandas as pd
from db import get_conn
from pages import genel_bakis, hisse_detay, degerlendirme, sistem, ecdf, backtest

st.set_page_config(
    page_title="Minerva — Anomali Tespiti",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    .stApp { background-color: #0a0a0f; color: #e0e0e0; }
    section[data-testid="stSidebar"] { display: none; }
    div[data-baseweb="select"] { background: #0f0f1a !important; border: 1px solid #1e1e2e !important; }
    .stButton button {
        background: #0f0f1a !important; border: 1px solid #1e1e2e !important;
        color: #a0a0c0 !important; font-family: 'IBM Plex Mono', monospace !important;
        font-size: 11px !important; letter-spacing: 0.08em !important;
        border-radius: 2px !important;
    }
    .stButton button:hover { border-color: #3b82f6 !important; color: #3b82f6 !important; }
    .stTextArea textarea {
        background: #0f0f1a !important; border: 1px solid #1e1e2e !important;
        color: #e0e0e0 !important; font-family: 'IBM Plex Mono', monospace !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 11px !important; letter-spacing: 0.08em !important;
        color: #666680 !important;
    }
    .stTabs [aria-selected="true"] { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:20px 0 16px 0;border-bottom:1px solid #1e1e2e;margin-bottom:24px">
    <div style="font-family:IBM Plex Mono;font-size:18px;font-weight:500;
                color:#ffffff;letter-spacing:0.08em">
        MINERVA<span style="color:#3b82f6">.</span>BIST
    </div>
    <div style="font-family:IBM Plex Mono;font-size:10px;color:#3b82f6;
                border:1px solid #1e3a5f;padding:3px 8px;border-radius:2px;
                letter-spacing:0.1em">
        FAZ A — ANOMALİ TESPİTİ
    </div>
</div>
""", unsafe_allow_html=True)

# Nav + Hisse seçimi
col_nav, col_hisse = st.columns([7, 2])

with col_nav:
    sayfa = st.radio(
        "Sayfa",
        ["Genel Bakis", "Hisse Detay", "Degerlendirme", "ECDF", "Backtest", "Sistem"],
        horizontal=True,
        label_visibility="collapsed"
    )

with col_hisse:
    conn = get_conn()
    hisseler = pd.read_sql(
        "SELECT symbol FROM stocks WHERE is_active = true ORDER BY symbol",
        conn
    )
    secilen = st.selectbox(
        "Hisse",
        hisseler["symbol"].tolist(),
        label_visibility="collapsed"
    )

st.markdown("<hr style='border:none;border-top:1px solid #1e1e2e;margin:0 0 24px 0'>", unsafe_allow_html=True)

# Sayfa yönlendirme
if sayfa == "Genel Bakis":
    genel_bakis.goster()
elif sayfa == "Hisse Detay":
    hisse_detay.goster(secilen)
elif sayfa == "Degerlendirme":
    degerlendirme.goster(secilen)
elif sayfa == "ECDF":
    ecdf.goster(secilen)
elif sayfa == "Backtest":
    backtest.goster()
elif sayfa == "Sistem":
    sistem.goster()
