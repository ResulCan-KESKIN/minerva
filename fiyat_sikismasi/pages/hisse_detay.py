import streamlit as st
import pandas as pd
from db import get_conn
from data_access import (
    fiyat_verisi_cek, anomali_tarihleri_cek, sikisma_kayitlari_cek
)
from components.grafik_kutu import grafik_kutu_goster
from components.faz_kart import faz_metrikler_goster


def _sec_header(n, title):
    st.markdown(
        f'<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;'
        f'margin:20px 0 14px 0">'
        f'<span style="color:#2e2e48;margin-right:8px">§ {n}</span>{title}</div>',
        unsafe_allow_html=True,
    )


def goster(symbol: str):
    conn = get_conn()

    # Hisse ID
    df_stocks = pd.read_sql(
        "SELECT id FROM stocks WHERE symbol = %s AND is_active = true",
        conn, params=(symbol,)
    )
    if df_stocks.empty:
        st.warning(f"{symbol} bulunamadı.")
        return

    stock_id = int(df_stocks.iloc[0]["id"])

    _sec_header(1, f"{symbol} — Fiyat Grafiği")

    df_fiyat    = fiyat_verisi_cek(conn, stock_id, gun=250)
    anomaliler  = anomali_tarihleri_cek(conn, symbol)
    df_kayitlar = sikisma_kayitlari_cek(conn, symbol)

    # Kutu verilerini grafik formatına çevir
    kutular = []
    for _, row in df_kayitlar.iterrows():
        kutular.append({
            "baslangic": row["kutu_baslangic"],
            "bitis":     row["kutu_bitis"],
            "radar":     row["radar"],
            "zirve":     row.get("cekirdek_zirve") or 0,
            "dip":       row.get("cekirdek_dip") or 0,
        })

    grafik_kutu_goster(
        df_fiyat, kutular, anomali_tarihleri=anomaliler,
        key=f"grafik_{symbol}", yukseklik=420
    )

    # Son kayıt için metrik kartları
    _sec_header(2, "Son Sıkışma Metrikleri")

    if df_kayitlar.empty:
        st.markdown('<div style="color:#3a3a55;font-size:11px">Bu hisse için sıkışma kaydı yok.</div>',
                    unsafe_allow_html=True)
        return

    son = df_kayitlar.iloc[0]
    faz_metrikler_goster(
        pencere_gun=int(son["pencere_uzunlugu"]) if pd.notna(son.get("pencere_uzunlugu")) else None,
        fiziki_limit=float(son["fiziki_limit"]) if pd.notna(son.get("fiziki_limit")) else None,
        efor_rasyosu=float(son["efor_rasyosu"]) if pd.notna(son.get("efor_rasyosu")) else None,
        sok_sayisi=int(son["sok_sayisi"]) if pd.notna(son.get("sok_sayisi")) else None,
        sok_hacim_yuzdesi=float(son["sok_hacim_yuzdesi"]) if pd.notna(son.get("sok_hacim_yuzdesi")) else None,
    )

    # Tüm kayıtlar tablosu
    if len(df_kayitlar) > 1:
        _sec_header(3, "Tüm Sıkışma Geçmişi")
        for _, row in df_kayitlar.iterrows():
            radar_renk = "#4d8ef0" if row["radar"] == "radar1" else "#d4820a"
            efor = f'{row["efor_rasyosu"]:.3f}x' if pd.notna(row.get("efor_rasyosu")) else "—"
            st.markdown(
                f'<div style="display:flex;gap:20px;padding:8px 0;'
                f'border-bottom:1px solid #0f0f18;font-size:11px">'
                f'<span style="color:{radar_renk};width:60px">{row["radar"].upper()}</span>'
                f'<span style="color:#6a6a88">{str(row["kutu_baslangic"])} → {str(row["kutu_bitis"])}</span>'
                f'<span style="color:#4a4a68">{int(row["pencere_uzunlugu"]) if pd.notna(row.get("pencere_uzunlugu")) else "—"}g</span>'
                f'<span style="color:#e0e0f0">efor {efor}</span>'
                f'<span style="color:#d4820a">şok {int(row["sok_sayisi"]) if pd.notna(row.get("sok_sayisi")) else "—"}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
