import streamlit as st

def metrik_kart(label, value, renk="normal"):
    renkler = {
        "normal": "#ffffff",
        "warn": "#f59e0b",
        "danger": "#ef4444",
        "ok": "#10b981"
    }
    st.markdown(f"""
    <div style="background:#0f0f1a;border:1px solid #1e1e2e;border-radius:4px;padding:16px 20px">
        <div style="font-size:10px;font-weight:500;color:#666680;letter-spacing:0.12em;
                    text-transform:uppercase;margin-bottom:6px">{label}</div>
        <div style="font-family:IBM Plex Mono;font-size:24px;font-weight:500;
                    color:{renkler[renk]}">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def feature_panel_goster(feature_df):
    son = feature_df.iloc[-1]

    # RVOL
    st.markdown('<div style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:0.15em;text-transform:uppercase;margin:24px 0 12px">Goreceli Hacim — RVOL</div>', unsafe_allow_html=True)
    st.caption("1.0 = normal hacim")
    c1, c2 = st.columns(2)
    rvol5 = son["rvol_5g"]
    rvol20 = son["rvol_20g"]
    with c1:
        metrik_kart("RVOL 5G", f"{rvol5:.2f}x", "danger" if rvol5 > 2 else ("warn" if rvol5 > 1.5 else "ok"))
    with c2:
        metrik_kart("RVOL 20G", f"{rvol20:.2f}x", "danger" if rvol20 > 2 else ("warn" if rvol20 > 1.5 else "ok"))
    st.line_chart(feature_df.set_index("tarih")[["rvol_5g", "rvol_20g"]])

    st.markdown("<hr style='border:none;border-top:1px solid #1e1e2e;margin:24px 0'>", unsafe_allow_html=True)

    # Volatilite
    st.markdown('<div style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:12px">Volatilite</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: metrik_kart("VOL 5G", f"{son['volatilite_5g']:.4f}")
    with c2: metrik_kart("VOL 20G", f"{son['volatilite_20g']:.4f}")
    with c3: metrik_kart("VOL 60G", f"{son['volatilite_60g']:.4f}")
    st.line_chart(feature_df.set_index("tarih")[["volatilite_5g", "volatilite_20g", "volatilite_60g"]])

    st.markdown("<hr style='border:none;border-top:1px solid #1e1e2e;margin:24px 0'>", unsafe_allow_html=True)

    # Fiyat değişimi
    st.markdown('<div style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:12px">Kumulatif Fiyat Degisimi</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    for col, key, label in [
        (c1, "fiyat_degisimi_5g", "5 GUNLUK"),
        (c2, "fiyat_degisimi_20g", "20 GUNLUK"),
        (c3, "fiyat_degisimi_60g", "60 GUNLUK")
    ]:
        val = son[key] * 100
        with col:
            metrik_kart(label, f"{val:+.2f}%", "danger" if val < -5 else ("ok" if val > 5 else "warn"))

    st.markdown("<hr style='border:none;border-top:1px solid #1e1e2e;margin:24px 0'>", unsafe_allow_html=True)

    # Bant genişliği
    st.markdown('<div style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:12px">Fiyat Bant Genisligi</div>', unsafe_allow_html=True)
    st.caption("Daralma = sıkışma sinyali")
    st.line_chart(feature_df.set_index("tarih")[["fiyat_bant_genisligi_5g", "fiyat_bant_genisligi_20g"]])