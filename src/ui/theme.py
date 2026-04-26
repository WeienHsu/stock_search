import streamlit as st


def apply_theme() -> None:
    st.markdown("""
    <style>
    /* ── 莫蘭迪底色 ── */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #F5F2EE;
        color: #4A4540;
    }
    [data-testid="stSidebar"] {
        background-color: #EDE9E4;
        border-right: 1px solid #D4CEC8;
    }
    /* ── 卡片容器 ── */
    [data-testid="stVerticalBlock"] > div:first-child {
        gap: 0.75rem;
    }
    /* ── 指標面板標題 ── */
    h3 { color: #4A4540; font-weight: 500; }
    /* ── 按鈕 ── */
    .stButton > button {
        background-color: #D4CEC8;
        color: #4A4540;
        border: none;
        border-radius: 6px;
    }
    .stButton > button:hover { background-color: #C8A86A; color: #fff; }
    /* ── 訊號燈 ── */
    .signal-buy  { color: #7DAA92; font-weight: 600; }
    .signal-sell { color: #C47E7E; font-weight: 600; }
    .signal-none { color: #8A8480; }
    </style>
    """, unsafe_allow_html=True)
