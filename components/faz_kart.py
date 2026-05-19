"""
Faz 2 / 3 / 4 metrik kartları.
Radar 1: Pencere · Fiziki Limit · Efor Rasyosu · Şok Günü · Şok Hacim
Radar 2 v2: Geçen Gün · AVWAP Sapma · Efor (20g) · Fiziki Limit · Şok Günü · Şok Hacim
"""

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
    pencere_gun: int | None,
    fiziki_limit: float | None,
    efor_rasyosu: float | None,
    sok_sayisi: int | None,
    sok_hacim_yuzdesi: float | None,
    # Radar 2 v2 ek alanlar
    radar: str = "radar1",
    avwap_sapma: float | None = None,
    kopus_yonu: str | None = None,
):
    if radar == "radar2" and avwap_sapma is not None:
        c1, c2, c3, c4, c5, c6 = st.columns(6)

        # ── Radar 2 v2 kartları ───────────────────────────────────────────────
        # Kart 1: Geçen Gün
        with c1:
            val  = f"{pencere_gun}g" if pencere_gun else "—"
            renk = "#e84040" if (pencere_gun or 0) > 90 else (
                   "#d4820a" if (pencere_gun or 0) > 60 else "#e0e0f0")
            _kart("Geçen Gün", val, renk, "T0'dan bu yana")

        # Kart 2: AVWAP Sapma
        with c2:
            sapma_abs = abs(avwap_sapma)
            if sapma_abs < 2:
                renk = "#22c55e"
                alt  = "yapışık"
            elif sapma_abs < 5:
                renk = "#d4820a"
                alt  = "ılımlı sapma"
            else:
                renk = "#e84040"
                alt  = "kopuşa yakın"
            isaretli = f"+{avwap_sapma:.2f}%" if avwap_sapma >= 0 else f"{avwap_sapma:.2f}%"
            _kart("AVWAP Sapma", isaretli, renk, alt)

        # Kart 3: Efor Rasyosu (kayan 20g)
        with c3:
            val  = f"{efor_rasyosu:.3f}x" if efor_rasyosu is not None else "—"
            renk = "#22c55e" if (efor_rasyosu or 0) >= 1.5 else "#e0e0f0"
            _kart("Efor (20g)", val, renk, "son 20g kayan pencere")

        # Kart 4: Fiziki Limit
        with c4:
            val  = f"{fiziki_limit:.4f}" if fiziki_limit is not None else "—"
            renk = "#22c55e" if (fiziki_limit or 0) >= 0.30 else "#4d8ef0"
            _kart("Fiziki Limit", val, renk, "emilim hacim / dolaşım")

        # Kart 5: Şok Günü
        with c5:
            val  = str(sok_sayisi) if sok_sayisi is not None else "—"
            renk = "#d4820a" if (sok_sayisi or 0) >= 3 else "#e0e0f0"
            _kart("Şok Günü", val, renk, "anomali gün sayısı")

        # Kart 6: Şok Hacim
        with c6:
            val  = f"%{sok_hacim_yuzdesi:.1f}" if sok_hacim_yuzdesi is not None else "—"
            renk = "#22c55e" if (sok_hacim_yuzdesi or 0) >= 30 else "#e0e0f0"
            _kart("Şok Hacim", val, renk, "şok günleri / emilim")

    else:
        c1, c2, c3, c4, c5 = st.columns(5)
        # ── Radar 1 kartları (mevcut davranış) ───────────────────────────────
        with c1:
            _kart("Pencere", f"{pencere_gun}g" if pencere_gun else "—")

        with c2:
            val  = f"{fiziki_limit:.4f}" if fiziki_limit is not None else "—"
            _kart("Fiziki Limit", val, "#4d8ef0", "hacim / dolaşım lot")

        with c3:
            val  = f"{efor_rasyosu:.3f}x" if efor_rasyosu is not None else "—"
            renk = "#22c55e" if (efor_rasyosu or 0) >= 1.5 else "#e0e0f0"
            _kart("Efor Rasyosu", val, renk, "kutu hacmi / normal dönem")

        with c4:
            val  = str(sok_sayisi) if sok_sayisi is not None else "—"
            renk = "#d4820a" if (sok_sayisi or 0) >= 3 else "#e0e0f0"
            _kart("Şok Günü", val, renk, "anomali gün sayısı")

        with c5:
            val  = f"%{sok_hacim_yuzdesi:.1f}" if sok_hacim_yuzdesi is not None else "—"
            renk = "#d4820a" if (sok_hacim_yuzdesi or 0) >= 30 else "#e0e0f0"
            _kart("Şok Hacim", val, renk, "şok günleri / toplam")
