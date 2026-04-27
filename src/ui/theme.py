import streamlit as st


def apply_theme() -> None:
    import config.morandi_palette as morandi
    import config.dark_palette as dark_pal

    P = dark_pal if st.session_state.get("theme") == "dark" else morandi

    st.markdown(f"""
    <style>
    html, body, [data-testid="stAppViewContainer"] {{
        background-color: {P.BACKGROUND};
        color: {P.TEXT_PRIMARY};
    }}
    [data-testid="stSidebar"] {{
        background-color: {P.SURFACE};
        border-right: 1px solid {P.BORDER};
    }}
    [data-testid="stVerticalBlock"] > div:first-child {{
        gap: 0.75rem;
    }}
    h3 {{ color: {P.TEXT_PRIMARY}; font-weight: 500; }}
    .stButton > button {{
        background-color: {P.BORDER};
        color: {P.TEXT_PRIMARY};
        border: none;
        border-radius: 6px;
    }}
    .stButton > button:hover {{ background-color: {P.GOLD}; color: #fff; }}
    .signal-buy  {{ color: {P.GREEN}; font-weight: 600; }}
    .signal-sell {{ color: {P.RED}; font-weight: 600; }}
    .signal-none {{ color: {P.TEXT_SECONDARY}; }}
    </style>
    """, unsafe_allow_html=True)
