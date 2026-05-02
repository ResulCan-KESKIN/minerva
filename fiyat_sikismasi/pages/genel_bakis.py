import streamlit as st
import pandas as pd
from db import get_conn
from data_access import sikisma_kayitlari_cek, ozet_metrikler_cek


def _sec_header(n, title):
    st.markdown(
        f'<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;'
        f'margin:20px 0 14px 0">'
        f'<span style="color:#2e2e48;margin-right:8px">§ {n}</span>{title}</div>',
        unsafe_allow_html=True,
    )


def goster():
    conn = get_conn()

    _sec_header(1, "Özet Metrikler")

    ozet = ozet_metrikler_cek(conn)
    son_str = str(ozet.get("son_guncelleme", "—"))[:10]

    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, renk in [
        (c1, "Takip Edilen",  int(ozet.get("hisse_sayisi", 0)),    "#e0e0f0"),
        (c2, "Sıkışma Kaydı", int(ozet.get("toplam_sikisma", 0)), "#e0e0f0"),
        (c3, "Radar 1",       int(ozet.get("radar1_sayisi", 0)),   "#4d8ef0"),
        (c4, "Radar 2",       int(ozet.get("radar2_sayisi", 0)),   "#d4820a"),
    ]:
        col.markdown(
            f'<div style="background:#0f0f18;border:1px solid #1a1a24;'
            f'border-radius:2px;padding:14px 16px;margin-bottom:20px">'
            f'<div style="font-size:9px;color:#3a3a55;letter-spacing:0.12em;'
            f'text-transform:uppercase;margin-bottom:6px">{label}</div>'
            f'<div style="font-size:26px;color:{renk};font-weight:300">{val:,}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div style="font-size:9px;color:#2e2e48;margin-bottom:20px">'
        f'Son güncelleme: <span style="color:#4a4a68">{son_str}</span></div>',
        unsafe_allow_html=True,
    )

    _sec_header(2, "Sıkışma Kayıtları")

    df = sikisma_kayitlari_cek(conn)
    if df.empty:
        st.markdown('<div style="color:#3a3a55;font-size:11px">Henüz kayıt yok.</div>',
                    unsafe_allow_html=True)
        return

    # Kolon başlıkları
    cols_template = "100px 70px 100px 100px 70px 90px 90px 80px 90px"
    st.markdown(
        f'<div style="display:grid;grid-template-columns:{cols_template};'
        f'gap:0;padding:7px 14px;border-bottom:1px solid #1a1a24;'
        f'font-size:9px;color:#2e2e48;letter-spacing:0.12em;text-transform:uppercase">'
        f'<span>Hisse</span><span>Radar</span><span>Başlangıç</span><span>Bitiş</span>'
        f'<span>Gün</span><span>Efor Rasyosu</span><span>Fiziki Limit</span>'
        f'<span>Şok</span><span>Şok Hacim %</span></div>',
        unsafe_allow_html=True,
    )

    for _, row in df.iterrows():
        radar_renk = "#4d8ef0" if row["radar"] == "radar1" else "#d4820a"
        efor_str  = f'{row["efor_rasyosu"]:.3f}x' if pd.notna(row.get("efor_rasyosu")) else "—"
        fizik_str = f'{row["fiziki_limit"]:.4f}' if pd.notna(row.get("fiziki_limit")) else "—"
        sok_yuz   = f'%{row["sok_hacim_yuzdesi"]:.1f}' if pd.notna(row.get("sok_hacim_yuzdesi")) else "—"

        st.markdown(
            f'<div style="display:grid;grid-template-columns:{cols_template};'
            f'gap:0;padding:9px 14px;border-bottom:1px solid #0f0f18;align-items:center">'
            f'<span style="font-size:12px;color:#e0e0f0">{row["symbol"]}</span>'
            f'<span style="font-size:10px;color:{radar_renk}">{row["radar"].upper()}</span>'
            f'<span style="font-size:11px;color:#6a6a88">{str(row["kutu_baslangic"])}</span>'
            f'<span style="font-size:11px;color:#6a6a88">{str(row["kutu_bitis"])}</span>'
            f'<span style="font-size:11px;color:#4a4a68">{int(row["pencere_uzunlugu"]) if pd.notna(row.get("pencere_uzunlugu")) else "—"}</span>'
            f'<span style="font-size:11px;color:#e0e0f0">{efor_str}</span>'
            f'<span style="font-size:11px;color:#4a4a68">{fizik_str}</span>'
            f'<span style="font-size:11px;color:#d4820a">{int(row["sok_sayisi"]) if pd.notna(row.get("sok_sayisi")) else "—"}</span>'
            f'<span style="font-size:11px;color:#d4820a">{sok_yuz}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
