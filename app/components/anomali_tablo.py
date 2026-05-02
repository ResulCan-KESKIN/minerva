import streamlit as st

TIP_BADGE_MAP = {
    "anomali_z60":   ("#4d8ef0", "Z60"),
    "anomali_z120":  ("#06b6d4", "Z120"),
    "anomali_rz60":  ("#d4820a", "RZ60"),
    "anomali_rz120": ("#22c55e", "RZ120"),
    "anomali_t":     ("#a07af0", "T"),
}


def tip_badge(tip):
    renk, etiket = TIP_BADGE_MAP.get(tip, ("#3a3a55", tip))
    return (
        f'<span style="border:1px solid {renk};color:{renk};'
        f'font-size:10px;padding:1px 5px;border-radius:2px;'
        f'letter-spacing:0.04em;white-space:nowrap">{etiket}</span>'
    )


def durum_badge(durum):
    if "onaylandi" in str(durum):
        return '<span style="font-size:10px;color:#e84040">ONAYLANDI</span>'
    elif "ret" in str(durum):
        return '<span style="font-size:10px;color:#22c55e">RET</span>'
    return '<span style="font-size:10px;color:#d4820a">BEKLEMEDE</span>'


def anomali_tablo_goster(anomaliler):
    st.markdown(
        '<div style="display:grid;grid-template-columns:90px 70px 70px 90px;'
        'gap:0;padding:6px 12px;border-bottom:1px solid #1a1a24;'
        'font-size:9px;color:#2e2e48;letter-spacing:0.1em;text-transform:uppercase">'
        '<span>Tarih</span><span>Tip</span><span>Skor</span><span>Durum</span></div>',
        unsafe_allow_html=True,
    )
    for _, row in anomaliler.iterrows():
        tarih = str(row["baslangic_zaman"])[:10]
        st.markdown(
            f'<div style="display:grid;grid-template-columns:90px 70px 70px 90px;'
            f'gap:0;padding:8px 12px;border-bottom:1px solid #0f0f18;align-items:center">'
            f'<span style="font-size:11px;color:#8888a8">{tarih}</span>'
            f'<span>{tip_badge(row["anomali_tipi"])}</span>'
            f'<span style="font-size:11px;color:#4a4a68">{row["skor"]:.4f}</span>'
            f'{durum_badge(row["durum"])}'
            f'</div>',
            unsafe_allow_html=True,
        )
