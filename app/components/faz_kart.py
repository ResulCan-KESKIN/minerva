import streamlit as st


def _kart(label: str, value: str, renk: str = "#e0e0f0", alt: str = ""):
    alt_html = (
        f'<div style="font-size:9px;color:#3a3a55;margin-top:4px">{alt}</div>'
        if alt else ""
    )
    st.markdown(
        f'<div style="background:#0f0f18;border:1px solid #1a1a24;'
        f'border-radius:2px;padding:12px 16px;margin-bottom:16px">'
        f'<div style="font-size:9px;color:#3a3a55;letter-spacing:0.12em;'
        f'text-transform:uppercase;margin-bottom:6px">{label}</div>'
        f'<div style="font-size:22px;color:{renk};font-weight:300">{value}</div>'
        f'{alt_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def faz_metrikler_goster(
    pencere_gun,
    fiziki_limit,
    efor_rasyosu,
    sok_sayisi,
    sok_hacim_yuzdesi,
):
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        _kart("Pencere", f"{pencere_gun}g" if pencere_gun else "—")

    with c2:
        val = f"{fiziki_limit:.4f}" if fiziki_limit is not None else "—"
        _kart("Fiziki Limit", val, "#4d8ef0", "hacim / dolaşım lot")

    with c3:
        val = f"{efor_rasyosu:.3f}x" if efor_rasyosu is not None else "—"
        renk = "#22c55e" if (efor_rasyosu or 0) >= 1.5 else "#e0e0f0"
        _kart("Efor Rasyosu", val, renk, "kutu hacmi / normal dönem")

    with c4:
        val = str(sok_sayisi) if sok_sayisi is not None else "—"
        renk = "#d4820a" if (sok_sayisi or 0) >= 3 else "#e0e0f0"
        _kart("Şok Günü", val, renk, "anomali gün sayısı")

    with c5:
        val = f"%{sok_hacim_yuzdesi:.1f}" if sok_hacim_yuzdesi is not None else "—"
        renk = "#d4820a" if (sok_hacim_yuzdesi or 0) >= 30 else "#e0e0f0"
        _kart("Şok Hacim", val, renk, "şok günleri / toplam")
