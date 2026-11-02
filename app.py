from __future__ import annotations

import streamlit as st

from bairroiq.ui import apply_theme

st.set_page_config(
    page_title="BairroIQ | Atlas Sampa",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


pages = [
    st.Page(
        "pages/explorar.py",
        title="Explorar / Mapa",
        icon="🗺️",
        default=True,
    ),
    st.Page(
        "pages/comparar.py",
        title="Comparar regiões",
        icon="📊",
    ),
    st.Page(
        "pages/perfis.py",
        title="Perfis Urbanos",
        icon="🏘️",
    ),
    st.Page(
        "pages/fontes.py",
        title="Fontes",
        icon="📚",
    ),
]
navigation = st.navigation(pages, position="hidden")
st.session_state.setdefault("bairroiq-theme", "dark")
apply_theme()
navigation.run()
