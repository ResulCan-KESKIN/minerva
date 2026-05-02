import streamlit as st
import plotly.graph_objects as go

CHART_BG   = "#0c0c13"
PLOT_BG    = "#0c0c13"
GRID_COLOR = "#0f0f18"

SIGMA_LINES = [
    ( 3, "#e84040", 0.9, "+3σ"),
    ( 2, "#d4820a", 0.7, "+2σ"),
    (-2, "#d4820a", 0.7, "−2σ"),
    (-3, "#e84040", 0.9, "−3σ"),
]


def _renk_val(val):
    av = abs(val)
    if av >= 3:   return "#e84040"
    if av >= 2:   return "#d4820a"
    return "#4a4a68"


def _zscore_fig(df, seri_a, seri_b, renk_a="#e0e0f0", renk_b="#3a3a55"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["tarih"], y=df[seri_a],
        mode="lines", name=seri_a,
        line=dict(color=renk_a, width=1),
        hovertemplate="%{y:.3f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["tarih"], y=df[seri_b],
        mode="lines", name=seri_b,
        line=dict(color=renk_b, width=1, dash="dot"),
        hovertemplate="%{y:.3f}<extra></extra>",
    ))
    for sigma, renk, opaklık, etiket in SIGMA_LINES:
        fig.add_hline(
            y=sigma,
            line_dash="dot",
            line_color=renk,
            line_width=1,
            opacity=opaklık,
            annotation_text=etiket,
            annotation_position="right",
            annotation_font=dict(size=9, color=renk, family="IBM Plex Mono"),
        )
    fig.update_layout(
        paper_bgcolor=CHART_BG,
        plot_bgcolor=PLOT_BG,
        margin=dict(l=40, r=52, t=8, b=24),
        height=160,
        showlegend=False,
        hovermode="x unified",
        xaxis=dict(
            gridcolor=GRID_COLOR,
            tickfont=dict(size=9, color="#3a3a55", family="IBM Plex Mono"),
            showline=False,
        ),
        yaxis=dict(
            gridcolor=GRID_COLOR,
            tickfont=dict(size=9, color="#3a3a55", family="IBM Plex Mono"),
            zeroline=False,
        ),
        font=dict(family="IBM Plex Mono"),
    )
    return fig


def _sec_label(title, val_a, label_a, val_b, label_b):
    ra = _renk_val(val_a)
    rb = _renk_val(val_b)
    st.markdown(
        f'<div style="font-size:10px;color:#3a3a55;letter-spacing:0.08em;'
        f'text-transform:uppercase;margin:18px 0 4px 0;display:flex;'
        f'align-items:center;justify-content:space-between">'
        f'<span style="color:#2a2a40">{title}</span>'
        f'<span>'
        f'<span style="color:#2e2e48">{label_a}·</span>'
        f'<span style="color:{ra}">{val_a:+.3f}</span>'
        f'&nbsp;&nbsp;'
        f'<span style="color:#2e2e48">{label_b}·</span>'
        f'<span style="color:{rb}">{val_b:+.3f}</span>'
        f'</span></div>',
        unsafe_allow_html=True,
    )


def zscore_panel_goster(zscore_df):
    son = zscore_df.iloc[-1]

    z60  = float(son["z_score_60"])
    z120 = float(son["z_score_120"])
    rz60 = float(son["z_score_robust_60"])
    rz120= float(son["z_score_robust_120"])

    _sec_label("Z-Score — Klasik", z60, "z60", z120, "z120")
    st.plotly_chart(
        _zscore_fig(zscore_df, "z_score_60", "z_score_120"),
        use_container_width=True, config={"displayModeBar": False},
    )

    _sec_label("Z-Score — Robust (MAD)", rz60, "rz60", rz120, "rz120")
    st.plotly_chart(
        _zscore_fig(zscore_df, "z_score_robust_60", "z_score_robust_120"),
        use_container_width=True, config={"displayModeBar": False},
    )

    st.markdown(
        '<div style="font-size:10px;color:#2a2a40;letter-spacing:0.1em;'
        'text-transform:uppercase;margin:16px 0 8px 0">'
        'Son 10 Gün · Z-Değerleri</div>',
        unsafe_allow_html=True,
    )

    def _renk_html(val):
        av = abs(val)
        if av >= 3: return "#e84040"
        if av >= 2: return "#d4820a"
        return "#4a4a68"

    son10 = zscore_df.tail(10).copy()
    son10["tarih"] = son10["tarih"].dt.strftime("%Y-%m-%d")

    st.markdown(
        '<div style="display:grid;grid-template-columns:100px 70px 70px 80px 80px;'
        'gap:0;padding:6px 12px;border-bottom:1px solid #1a1a24;'
        'font-size:9px;color:#2e2e48;letter-spacing:0.1em;text-transform:uppercase">'
        '<span>Tarih</span><span>Z60</span><span>Z120</span>'
        '<span>RZ60</span><span>RZ120</span></div>',
        unsafe_allow_html=True,
    )
    for _, row in son10.iterrows():
        st.markdown(
            f'<div style="display:grid;grid-template-columns:100px 70px 70px 80px 80px;'
            f'gap:0;padding:7px 12px;border-bottom:1px solid #0f0f18">'
            f'<span style="font-size:10px;color:#3a3a55">{row["tarih"]}</span>'
            f'<span style="font-size:10px;color:{_renk_html(row["z_score_60"])}">{row["z_score_60"]:.3f}</span>'
            f'<span style="font-size:10px;color:{_renk_html(row["z_score_120"])}">{row["z_score_120"]:.3f}</span>'
            f'<span style="font-size:10px;color:{_renk_html(row["z_score_robust_60"])}">{row["z_score_robust_60"]:.3f}</span>'
            f'<span style="font-size:10px;color:{_renk_html(row["z_score_robust_120"])}">{row["z_score_robust_120"]:.3f}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
