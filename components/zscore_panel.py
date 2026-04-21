# components/zscore_panel.py
# feature_panel.py'nin yerini alıyor — Z-Score ve Robust Z-Score gösterimi
import streamlit as st

def metrik_kart(label, value, renk="normal"):
    renkler = {
        "normal": "#ffffff",
        "warn":   "#f59e0b",
        "danger": "#ef4444",
        "ok":     "#10b981"
    }
    st.markdown(f"""
    <div style="background:#0f0f1a;border:1px solid #1e1e2e;border-radius:4px;padding:16px 20px">
        <div style="font-size:10px;font-weight:500;color:#666680;letter-spacing:0.12em;
                    text-transform:uppercase;margin-bottom:6px">{label}</div>
        <div style="font-family:IBM Plex Mono;font-size:24px;font-weight:500;
                    color:{renkler[renk]}">{value}</div>
    </div>
    """, unsafe_allow_html=True)


def _renk(val, esik_warn=2.0, esik_danger=3.0):
    abs_val = abs(val)
    if abs_val >= esik_danger:
        return "danger"
    elif abs_val >= esik_warn:
        return "warn"
    return "ok"


def zscore_panel_goster(zscore_df):
    son = zscore_df.iloc[-1]

    # ── Klasik Z-Score ──
    st.markdown('<div style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:0.15em;text-transform:uppercase;margin:24px 0 12px">Klasik Z-Score</div>', unsafe_allow_html=True)
    st.caption("|z| > 2 = anormal · |z| > 3 = kritik")

    c1, c2 = st.columns(2)
    with c1:
        val = son["z_score_60"]
        metrik_kart("Z-SCORE 60G", f"{val:.3f}", _renk(val))
    with c2:
        val = son["z_score_120"]
        metrik_kart("Z-SCORE 120G", f"{val:.3f}", _renk(val))

    st.line_chart(zscore_df.set_index("tarih")[["z_score_60", "z_score_120"]])

    st.markdown("<hr style='border:none;border-top:1px solid #1e1e2e;margin:24px 0'>", unsafe_allow_html=True)

    # ── Robust Z-Score ──
    st.markdown('<div style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:12px">Robust Z-Score (MAD)</div>', unsafe_allow_html=True)
    st.caption("Medyan ve MAD tabanlı — aykırı değerlere dirençli")

    c1, c2 = st.columns(2)
    with c1:
        val = son["z_score_robust_60"]
        metrik_kart("ROBUST Z 60G", f"{val:.3f}", _renk(val))
    with c2:
        val = son["z_score_robust_120"]
        metrik_kart("ROBUST Z 120G", f"{val:.3f}", _renk(val))

    st.line_chart(zscore_df.set_index("tarih")[["z_score_robust_60", "z_score_robust_120"]])

    st.markdown("<hr style='border:none;border-top:1px solid #1e1e2e;margin:24px 0'>", unsafe_allow_html=True)

    # ── Karşılaştırmalı tablo (son 10 gün) ──
    st.markdown('<div style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:12px">Son 10 Gun</div>', unsafe_allow_html=True)

    son10 = zscore_df.tail(10).copy()
    son10["tarih"] = son10["tarih"].dt.strftime("%Y-%m-%d")

    st.markdown("""
    <div style="display:grid;grid-template-columns:110px 90px 90px 110px 110px;gap:12px;
                padding:8px 12px;border-bottom:1px solid #1e1e2e;
                font-size:10px;color:#666680;letter-spacing:0.08em;text-transform:uppercase">
        <span>Tarih</span>
        <span>Z-60</span><span>Z-120</span>
        <span>Robust Z-60</span><span>Robust Z-120</span>
    </div>
    """, unsafe_allow_html=True)

    def _renk_html(val):
        if abs(val) >= 3:
            return "#ef4444"
        elif abs(val) >= 2:
            return "#f59e0b"
        return "#a0a0c0"

    for _, row in son10.iterrows():
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:110px 90px 90px 110px 110px;gap:12px;
                    padding:10px 12px;border-bottom:1px solid #111120;align-items:center">
            <span style="font-family:IBM Plex Mono;font-size:11px;color:#666680">{row['tarih']}</span>
            <span style="font-family:IBM Plex Mono;font-size:11px;color:{_renk_html(row['z_score_60'])}">{row['z_score_60']:.3f}</span>
            <span style="font-family:IBM Plex Mono;font-size:11px;color:{_renk_html(row['z_score_120'])}">{row['z_score_120']:.3f}</span>
            <span style="font-family:IBM Plex Mono;font-size:11px;color:{_renk_html(row['z_score_robust_60'])}">{row['z_score_robust_60']:.3f}</span>
            <span style="font-family:IBM Plex Mono;font-size:11px;color:{_renk_html(row['z_score_robust_120'])}">{row['z_score_robust_120']:.3f}</span>
        </div>
        """, unsafe_allow_html=True)
