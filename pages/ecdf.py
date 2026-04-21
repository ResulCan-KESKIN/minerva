# pages/ecdf.py — ECDF Analiz Sayfası
import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
import os


@st.cache_resource
def get_ext_conn():
    return psycopg2.connect(
        host=os.environ.get("EXT_DB_HOST", "aws-0-eu-west-1.pooler.supabase.com"),
        port=int(os.environ.get("EXT_DB_PORT", 6543)),
        database=os.environ.get("EXT_DB_NAME", "postgres"),
        user=os.environ.get("EXT_DB_USER", "postgres.ewetkqwkjbmblutbejsh"),
        password=os.environ.get("EXT_DB_PASSWORD", "QuantShine2025.")
    )


def ecdf_hesapla(seri: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Empirical CDF: x=sıralı değerler, y=kümülatif olasılık."""
    temiz = seri.dropna().sort_values().values
    n = len(temiz)
    return temiz, np.arange(1, n + 1) / n


def goster(secilen: str = None):
    st.markdown("""
    <div style="font-family:IBM Plex Mono;font-size:14px;font-weight:500;
                color:#ffffff;letter-spacing:0.06em;margin-bottom:4px">
        ECDF — EMPİRİK DAĞILIM ANALİZİ
    </div>
    <div style="font-family:IBM Plex Mono;font-size:11px;color:#666680;
                margin-bottom:24px">
        Z-Score · Robust Z-Score · 60g / 120g pencere karşılaştırması
    </div>
    """, unsafe_allow_html=True)

    ext_conn = get_ext_conn()

    # ── Hisse listesi ──
    hisseler_df = pd.read_sql("""
        SELECT symbol FROM stocks
        WHERE is_active = true
        ORDER BY symbol
    """, ext_conn)

    semboller = hisseler_df["symbol"].tolist()

    # Mevcut seçili hisseyle eşleştir (.IS varsa temizle)
    temiz_secilen = secilen.replace(".IS", "") if secilen else None
    default_idx = semboller.index(temiz_secilen) if temiz_secilen in semboller else 0

    col_sec, col_meta = st.columns([2, 8])
    with col_sec:
        secilen_sembol = st.selectbox(
            "Hisse",
            semboller,
            index=default_idx,
            key="ecdf_sec",
            label_visibility="collapsed"
        )

    # Stock ID
    id_df = pd.read_sql(
        "SELECT id FROM stocks WHERE symbol = %s",
        ext_conn, params=(secilen_sembol,)
    )
    if id_df.empty:
        st.warning("Hisse bulunamadı.")
        return

    stock_id = int(id_df["id"].iloc[0])

    # ── Z-Score verisi ──
    df = pd.read_sql("""
        SELECT
            price_date,
            z_log_60,
            z_log_120,
            rz_log_60,
            rz_log_120
        FROM minerva_signals
        WHERE stock_id = %s
        ORDER BY price_date
    """, ext_conn, params=(stock_id,))

    if df.empty:
        st.warning(f"{secilen_sembol} için veri bulunamadı.")
        return

    df["price_date"] = pd.to_datetime(df["price_date"])

    with col_meta:
        st.markdown(f"""
        <div style="display:flex;gap:24px;align-items:center;padding:6px 0">
            <span style="font-family:IBM Plex Mono;font-size:11px;color:#666680">
                VERİ <span style="color:#a0a0c0">{len(df)} gün</span>
            </span>
            <span style="font-family:IBM Plex Mono;font-size:11px;color:#666680">
                {df['price_date'].min().strftime('%d.%m.%Y')}
                <span style="color:#3b82f6">→</span>
                {df['price_date'].max().strftime('%d.%m.%Y')}
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ── ECDF Grafiği ──
    seriler = [
        ("Z-Score 60g",         "z_log_60",   "#3b82f6"),
        ("Z-Score 120g",        "z_log_120",  "#06b6d4"),
        ("Robust Z-Score 60g",  "rz_log_60",  "#f59e0b"),
        ("Robust Z-Score 120g", "rz_log_120", "#10b981"),
    ]

    try:
        import plotly.graph_objects as go

        fig = go.Figure()

        for etiket, kolon, renk in seriler:
            if kolon not in df.columns:
                continue
            x, y = ecdf_hesapla(df[kolon])
            fig.add_trace(go.Scatter(
                x=x, y=y,
                mode="lines",
                name=etiket,
                line=dict(color=renk, width=2),
                hovertemplate=(
                    f"<b>{etiket}</b><br>"
                    "Z-Score: %{x:.3f}<br>"
                    "CDF: %{y:.1%}<extra></extra>"
                )
            ))

        # Eşik çizgileri: ±2 (≈%95), ±3 (≈%99)
        for esik, etiket_esik, opaklık in [
            (-3, "−3σ", 0.4), (3, "+3σ", 0.4),
            (-2, "−2σ", 0.6), (2, "+2σ", 0.6),
        ]:
            fig.add_vline(
                x=esik,
                line_dash="dot",
                line_color=f"rgba(100,100,150,{opaklık})",
                line_width=1,
                annotation_text=etiket_esik,
                annotation_position="top",
                annotation_font=dict(color="#6b7280", size=10, family="IBM Plex Mono")
            )

        fig.update_layout(
            paper_bgcolor="#0a0a0f",
            plot_bgcolor="#0f0f1a",
            font=dict(family="IBM Plex Mono", color="#a0a0c0", size=11),
            xaxis=dict(
                title="Z-Score",
                gridcolor="#1a1a2e",
                zerolinecolor="#2d2d3d",
                tickfont=dict(size=10)
            ),
            yaxis=dict(
                title="Kümülatif Olasılık",
                gridcolor="#1a1a2e",
                zerolinecolor="#2d2d3d",
                tickformat=".0%",
                tickfont=dict(size=10),
                range=[0, 1]
            ),
            legend=dict(
                bgcolor="#0f0f1a",
                bordercolor="#1e1e2e",
                borderwidth=1,
                font=dict(size=10, family="IBM Plex Mono")
            ),
            margin=dict(l=60, r=40, t=30, b=60),
            height=480,
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.error("plotly kurulu değil → `pip install plotly`")
        return

    # ── İstatistik Kartları ──
    st.markdown("""
    <div style="font-family:IBM Plex Mono;font-size:11px;color:#444460;
                letter-spacing:0.08em;margin:20px 0 12px 0;
                border-top:1px solid #1e1e2e;padding-top:16px">
        İSTATİSTİK ÖZETİ
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(4)
    for i, (etiket, kolon, renk) in enumerate(seriler):
        with cols[i]:
            s = df[kolon].dropna()
            asiri = int((s.abs() > 2).sum())
            cok_asiri = int((s.abs() > 3).sum())
            st.markdown(f"""
            <div style="background:#0f0f1a;border:1px solid #1e1e2e;
                        border-left:2px solid {renk};border-radius:2px;
                        padding:12px;font-family:IBM Plex Mono">
                <div style="font-size:10px;color:#666680;
                            margin-bottom:10px;letter-spacing:0.06em">
                    {etiket.upper()}
                </div>
                <div style="font-size:13px;color:#e0e0e0;margin-bottom:2px">
                    μ = {s.mean():.3f}
                </div>
                <div style="font-size:11px;color:#a0a0c0;margin-bottom:2px">
                    σ = {s.std():.3f}
                </div>
                <div style="font-size:11px;color:#a0a0c0;margin-bottom:2px">
                    min / max
                </div>
                <div style="font-size:11px;color:#a0a0c0;margin-bottom:10px">
                    {s.min():.2f} / {s.max():.2f}
                </div>
                <div style="font-size:10px;color:#f59e0b;margin-bottom:2px">
                    |z|>2 → {asiri} gün
                </div>
                <div style="font-size:10px;color:#ef4444">
                    |z|>3 → {cok_asiri} gün
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Anomali Tablosu (bu hisse için kayıtlılar) ──
    st.markdown("""
    <div style="font-family:IBM Plex Mono;font-size:11px;color:#444460;
                letter-spacing:0.08em;margin:24px 0 12px 0;
                border-top:1px solid #1e1e2e;padding-top:16px">
        TESPİT EDİLEN ANOMALİLER
    </div>
    """, unsafe_allow_html=True)

    anomali_df = pd.read_sql("""
        SELECT
            baslangic_zaman::date AS tarih,
            anomali_tipi,
            skor,
            durum,
            kaynak
        FROM anomali_kayitlari
        WHERE hisse_kodu = %s
        ORDER BY baslangic_zaman DESC
        LIMIT 50
    """, ext_conn, params=(secilen_sembol,))

    if anomali_df.empty:
        st.markdown("""
        <div style="font-family:IBM Plex Mono;font-size:11px;color:#444460;
                    padding:16px;border:1px solid #1e1e2e;border-radius:2px">
            Bu hisse için henüz anomali kaydı yok.
        </div>
        """, unsafe_allow_html=True)
    else:
        def tip_badge(tip):
            renk_map = {
                "kesin_anomali": ("#ef4444", "● KESİN"),
                "anomali_z60":   ("#3b82f6", "Z-60"),
                "anomali_z120":  ("#06b6d4", "Z-120"),
                "anomali_rz60":  ("#f59e0b", "RZ-60"),
                "anomali_rz120": ("#10b981", "RZ-120"),
                "anomali_t":     ("#a78bfa", "T-DAĞILIM"),
            }
            renk, etiket = renk_map.get(tip, ("#666680", tip))
            return f'<span style="color:{renk};font-size:10px">{etiket}</span>'

        def durum_badge(durum):
            if "onaylandi" in str(durum):
                return '<span style="color:#ef4444;font-size:10px">ONAYLANDI</span>'
            elif "ret" in str(durum):
                return '<span style="color:#10b981;font-size:10px">RET</span>'
            return '<span style="color:#f59e0b;font-size:10px">BEKLEMEDE</span>'

        satirlar = ""
        for _, r in anomali_df.iterrows():
            satirlar += f"""
            <tr style="border-bottom:1px solid #1a1a2e">
                <td style="padding:8px;color:#a0a0c0;font-size:11px">{r['tarih']}</td>
                <td style="padding:8px">{tip_badge(r['anomali_tipi'])}</td>
                <td style="padding:8px;color:#a0a0c0;font-size:11px">{r['skor']:.4f}</td>
                <td style="padding:8px">{durum_badge(r['durum'])}</td>
                <td style="padding:8px;color:#666680;font-size:10px">{r['kaynak'] or '—'}</td>
            </tr>
            """

        st.markdown(f"""
        <table style="width:100%;border-collapse:collapse;
                      font-family:IBM Plex Mono;background:#0f0f1a;
                      border:1px solid #1e1e2e;border-radius:2px">
            <thead>
                <tr style="border-bottom:1px solid #1e1e2e">
                    <th style="padding:8px;color:#444460;font-size:10px;
                               font-weight:500;text-align:left">TARİH</th>
                    <th style="padding:8px;color:#444460;font-size:10px;
                               font-weight:500;text-align:left">TİP</th>
                    <th style="padding:8px;color:#444460;font-size:10px;
                               font-weight:500;text-align:left">SKOR</th>
                    <th style="padding:8px;color:#444460;font-size:10px;
                               font-weight:500;text-align:left">DURUM</th>
                    <th style="padding:8px;color:#444460;font-size:10px;
                               font-weight:500;text-align:left">KAYNAK</th>
                </tr>
            </thead>
            <tbody>{satirlar}</tbody>
        </table>
        """, unsafe_allow_html=True)
