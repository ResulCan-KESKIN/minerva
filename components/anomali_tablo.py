import streamlit as st

def durum_badge(durum):
    if "onaylandi" in durum:
        return '<span style="padding:2px 8px;background:#1c0000;color:#ef4444;border:1px solid #3d0000;border-radius:2px;font-size:11px;font-family:IBM Plex Mono">ONAYLANDI</span>'
    elif "ret" in durum:
        return '<span style="padding:2px 8px;background:#001c08;color:#10b981;border:1px solid #003018;border-radius:2px;font-size:11px;font-family:IBM Plex Mono">REDDEDİLDİ</span>'
    else:
        return '<span style="padding:2px 8px;background:#1c1c00;color:#f59e0b;border:1px solid #3d3000;border-radius:2px;font-size:11px;font-family:IBM Plex Mono">BEKLEMEDE</span>'

def anomali_tablo_goster(anomaliler):
    st.markdown("""
    <div style="display:grid;grid-template-columns:120px 100px 80px 1fr;gap:16px;
                padding:10px 16px;border-bottom:1px solid #1e1e2e;
                font-size:10px;color:#666680;letter-spacing:0.1em;text-transform:uppercase">
        <span>Tarih</span><span>Tip</span><span>Skor</span><span>Durum</span>
    </div>
    """, unsafe_allow_html=True)

    for _, row in anomaliler.iterrows():
        tarih = str(row["baslangic_zaman"])[:10]
        tip = row["anomali_tipi"].replace("_", " ").upper()
        skor = f"{row['skor']:.4f}"
        badge = durum_badge(row["durum"])

        st.markdown(f"""
        <div style="display:grid;grid-template-columns:120px 100px 80px 1fr;gap:16px;
                    padding:12px 16px;border-bottom:1px solid #111120;align-items:center">
            <span style="font-family:IBM Plex Mono;font-size:12px">{tarih}</span>
            <span style="font-size:11px;color:#a0a0c0">{tip}</span>
            <span style="font-family:IBM Plex Mono;font-size:12px;color:#666680">{skor}</span>
            {badge}
        </div>
        """, unsafe_allow_html=True)