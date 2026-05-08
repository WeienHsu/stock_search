import streamlit as st

from src.ui.theme.tokens import get_tokens


def inject_css(theme: str) -> None:
    T = get_tokens(theme)
    st.html(
        f"""
        <style>
        :root {{
            --bg-base: {T['bg_base']};
            --bg-surface: {T['bg_surface']};
            --bg-elevated: {T['bg_elevated']};
            --border-subtle: {T['border_subtle']};
            --border-default: {T['border_default']};
            --border-strong: {T['border_strong']};
            --focus-ring: {T['focus_ring']};
            --text-primary: {T['text_primary']};
            --text-secondary: {T['text_secondary']};
            --text-tertiary: {T['text_tertiary']};
            --semantic-up: {T['semantic_up_text']};
            --semantic-down: {T['semantic_down_text']};
            --signal-buy: {T['signal_buy']};
            --signal-sell: {T['signal_sell']};
            --font-ui: {T['font_ui']};
            --font-mono: {T['font_mono']};
        }}

        /* [1] Global font stack and base colors */
        html, body, [data-testid="stAppViewContainer"], .stMarkdown, .stText {{
            background-color: {T['bg_base']};
            color: {T['text_primary']};
            font-family: {T['font_ui']};
        }}
        [data-testid="stSidebar"] {{
            background-color: {T['bg_surface']};
            border-right: 1px solid {T['border_default']};
        }}
        [data-testid="stVerticalBlock"] > div:first-child {{
            gap: 0.75rem;
        }}
        h3 {{
            color: {T['text_primary']};
            font-weight: 500;
        }}

        /* [2] Tabular numbers */
        [data-testid="stMetricValue"],
        [data-testid="stMetricDelta"],
        .stDataFrame,
        .stDataFrame * {{
            font-variant-numeric: tabular-nums;
            font-feature-settings: "tnum" 1;
        }}

        /* [3] Metric typography */
        [data-testid="stMetricLabel"] {{
            color: {T['text_tertiary']};
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.02em;
        }}
        [data-testid="stMetricValue"] {{
            color: {T['text_primary']};
            font-size: 24px;
            font-weight: 600;
        }}
        [data-testid="stMetricDelta"] {{
            font-size: 13px;
            font-weight: 600;
        }}

        /* [4] TW market convention: red up, green down */
        [data-testid="stMetricDelta"] svg[data-testid="stMetricDeltaIcon-Up"] {{
            fill: {T['semantic_up_text']} !important;
        }}
        [data-testid="stMetricDelta"] svg[data-testid="stMetricDeltaIcon-Down"] {{
            fill: {T['semantic_down_text']} !important;
        }}
        [data-testid="stMetricDelta"]:has(svg[data-testid="stMetricDeltaIcon-Up"]) {{
            color: {T['semantic_up_text']} !important;
        }}
        [data-testid="stMetricDelta"]:has(svg[data-testid="stMetricDeltaIcon-Down"]) {{
            color: {T['semantic_down_text']} !important;
        }}

        /* [5] Tabs */
        [data-baseweb="tab-list"] {{
            border-bottom: 1px solid {T['border_default']};
        }}
        [data-baseweb="tab"][aria-selected="true"] {{
            color: {T['text_primary']} !important;
            border-bottom: 2px solid {T['border_strong']} !important;
        }}
        [data-baseweb="tab"][aria-selected="false"] {{
            color: {T['text_secondary']};
        }}

        /* [6] Expander */
        [data-testid="stExpander"] {{
            background-color: {T['bg_surface']};
            border: 1px solid {T['border_subtle']};
            border-radius: 6px;
        }}
        [data-testid="stExpander"] summary {{
            color: {T['text_primary']};
            font-weight: 600;
        }}

        /* [7] DataFrame */
        .stDataFrame [data-testid="stDataFrameHeader"] {{
            background-color: {T['bg_elevated']};
            color: {T['text_tertiary']};
            font-size: 12px;
            font-weight: 600;
        }}
        .stDataFrame [aria-selected="true"] {{
            background-color: {T['bg_elevated']} !important;
            border-left: 3px solid {T['border_strong']};
        }}

        /* [8] Buttons and hit areas */
        .stButton > button {{
            min-height: 36px;
            border-radius: 6px;
            font-weight: 500;
            transition: background-color 150ms ease, border-color 150ms ease;
        }}
        .stButton > button[kind="primary"] {{
            background-color: {T['signal_buy']};
            color: {T['text_inverse']};
            border: none;
        }}
        .stButton > button[kind="primary"]:hover {{
            background-color: {T['signal_buy']};
            filter: brightness(0.92);
        }}
        .stButton > button[kind="secondary"] {{
            background-color: {T['bg_elevated']};
            color: {T['text_primary']};
            border: 1px solid {T['border_default']};
        }}

        /* [9] Focus ring */
        button:focus-visible,
        input:focus-visible,
        textarea:focus-visible,
        select:focus-visible,
        [role="button"]:focus-visible,
        [role="tab"]:focus-visible,
        [role="radio"]:focus-visible,
        [role="checkbox"]:focus-visible,
        [tabindex]:focus-visible,
        [data-baseweb="button"]:focus-visible,
        [data-testid="stTextInput"] input:focus-visible,
        [data-testid="stSelectbox"] [data-baseweb="select"]:focus-visible,
        [data-testid="stCheckbox"] input:focus-visible + div,
        [data-baseweb="tab"]:focus-visible {{
            outline: 2px solid {T['focus_ring']} !important;
            outline-offset: 2px !important;
            border-radius: 4px;
        }}
        [data-testid="stDataFrame"] thead {{
            z-index: 1;
        }}

        /* [10] Signal classes */
        .signal-buy {{
            color: {T['signal_buy']};
            font-weight: 600;
        }}
        .signal-sell {{
            color: {T['signal_sell']};
            font-weight: 600;
        }}
        .signal-none {{
            color: {T['text_tertiary']};
        }}
        .signal-dot {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 6px;
            vertical-align: middle;
        }}
        .signal-dot.buy {{ background: {T['signal_buy']}; }}
        .signal-dot.sell {{ background: {T['signal_sell']}; }}
        .signal-dot.none {{ background: {T['text_tertiary']}; }}

        /* [11] Screen-reader only utility */
        .sr-only {{
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }}

        /* [12] Reduced motion */
        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
                scroll-behavior: auto !important;
            }}
            [data-testid="stSpinner"] svg {{
                animation: none !important;
            }}
        }}

        [data-testid="stCheckbox"] {{
            padding: 4px 0;
            min-height: 24px;
        }}
        .modebar-btn {{
            min-width: 28px !important;
            min-height: 28px !important;
        }}
        @media (max-width: 1024px) {{
            [data-testid="stButton"] button,
            [data-testid="stCheckbox"],
            [data-testid="baseButton-secondary"] {{
                min-height: 44px;
            }}
        }}

        @media (prefers-color-scheme: dark) {{
            html[data-theme="system"] body {{
                background-color: #1A1D21;
                color: #E8EAF0;
            }}
        }}
        </style>
        """
    )
