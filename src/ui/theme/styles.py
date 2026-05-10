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
            --sidebar-bg: {T['sidebar_bg']};
            --sidebar-nav-active-bg: {T['sidebar_nav_active_bg']};
            --control-bg: {T['control_bg']};
            --control-bg-hover: {T['control_bg_hover']};
            --control-bg-active: {T['control_bg_active']};
            --button-secondary-bg: {T['button_secondary_bg']};
            --button-secondary-hover-bg: {T['button_secondary_hover_bg']};
            --button-disabled-bg: {T['button_disabled_bg']};
            --button-disabled-text: {T['button_disabled_text']};
            --border-subtle: {T['border_subtle']};
            --border-default: {T['border_default']};
            --border-strong: {T['border_strong']};
            --focus-ring: {T['focus_ring']};
            --text-primary: {T['text_primary']};
            --text-secondary: {T['text_secondary']};
            --text-tertiary: {T['text_tertiary']};
            --sidebar-text-secondary: {T['sidebar_text_secondary']};
            --semantic-up: {T['semantic_up_text']};
            --semantic-down: {T['semantic_down_text']};
            --signal-buy: {T['signal_buy']};
            --signal-sell: {T['signal_sell']};
            --font-ui: {T['font_ui']};
            --font-mono: {T['font_mono']};
            --space-sm: {T['space_sm']};
            --space-md: {T['space_md']};
            --space-lg: {T['space_lg']};
            --radius-sm: {T['radius_sm']};
            --radius-md: {T['radius_md']};
            --motion-fast: {T['motion_fast']};
        }}

        /* [1] Global font stack and base colors */
        html, body, [data-testid="stAppViewContainer"], .stMarkdown, .stText {{
            background-color: {T['bg_base']};
            color: {T['text_primary']};
            font-family: {T['font_ui']};
        }}
        [data-testid="stSidebar"] {{
            background-color: var(--sidebar-bg);
            border-right: 1px solid {T['border_default']};
            color: {T['text_primary']};
        }}
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] [data-testid="stElementContainer"],
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
            background-color: transparent !important;
        }}
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] small,
        [data-testid="stSidebar"] div[data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {{
            color: {T['text_primary']} !important;
        }}
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] span,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
            color: var(--sidebar-text-secondary) !important;
        }}
        [data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
        [data-testid="stSidebar"] [data-testid="stSidebarNav"] span,
        [data-testid="stSidebar"] [data-testid="stSidebarNav"] p,
        [data-testid="stSidebar"] [data-testid="stSidebarNavLink"],
        [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {{
            color: var(--sidebar-text-secondary) !important;
        }}
        [data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
        [data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] span,
        [data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] p,
        [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"] {{
            background-color: var(--sidebar-nav-active-bg) !important;
            color: {T['text_primary']} !important;
        }}
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea {{
            background-color: var(--control-bg) !important;
            color: {T['text_primary']} !important;
            -webkit-text-fill-color: {T['text_primary']} !important;
            border-color: {T['border_default']} !important;
        }}
        [data-testid="stSidebar"] input::placeholder,
        [data-testid="stSidebar"] textarea::placeholder {{
            color: {T['text_tertiary']} !important;
            -webkit-text-fill-color: {T['text_tertiary']} !important;
            opacity: 1 !important;
        }}
        [data-testid="stSidebar"] [data-baseweb="input"],
        [data-testid="stSidebar"] [data-baseweb="select"],
        [data-testid="stSidebar"] [data-baseweb="popover"] {{
            background-color: var(--control-bg) !important;
            color: {T['text_primary']} !important;
            border-color: {T['border_default']} !important;
        }}
        [data-testid="stSidebar"] [data-baseweb="tag"],
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="select"] span {{
            background-color: transparent !important;
            color: {T['text_primary']} !important;
        }}
        [data-testid="stSidebar"] [data-baseweb="radio"] div,
        [data-testid="stSidebar"] [data-baseweb="checkbox"] div,
        [data-testid="stSidebar"] [data-testid="stCheckbox"] div,
        [data-testid="stSidebar"] [data-testid="stRadio"] div,
        [data-testid="stSidebar"] [data-testid="stSegmentedControl"] div,
        [data-testid="stSidebar"] [data-testid="stMultiSelect"] div {{
            color: {T['text_primary']} !important;
        }}
        [data-testid="stSidebar"] [data-testid="stSegmentedControl"] button,
        [data-testid="stSidebar"] [data-testid="baseButton-secondary"],
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {{
            background-color: var(--control-bg) !important;
            color: {T['text_primary']} !important;
            border-color: {T['border_default']} !important;
        }}
        [data-testid="stSidebar"] [data-testid="stSegmentedControl"] button:hover,
        [data-testid="stSidebar"] [data-testid="baseButton-secondary"]:hover,
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {{
            background-color: var(--control-bg-hover) !important;
            color: {T['text_primary']} !important;
            border-color: {T['border_strong']} !important;
        }}
        [data-testid="stVerticalBlock"] > div:first-child {{
            gap: var(--space-md);
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
            font-size: {T['font_size_sm']};
            font-weight: {T['font_weight_semibold']};
            letter-spacing: 0.02em;
        }}
        [data-testid="stMetricValue"] {{
            color: {T['text_primary']};
            font-size: {T['font_size_xl']};
            font-weight: {T['font_weight_semibold']};
        }}
        [data-testid="stMetricDelta"] {{
            font-size: {T['font_size_md']};
            font-weight: {T['font_weight_semibold']};
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
            color: {T['tab_selected_text']} !important;
            border-bottom: 2px solid {T['tab_selected_text']} !important;
        }}
        [data-baseweb="tab"][aria-selected="true"] [data-testid="stMarkdownContainer"],
        [data-baseweb="tab"][aria-selected="true"] [data-testid="stMarkdownContainer"] p {{
            color: {T['tab_selected_text']} !important;
        }}
        [data-baseweb="tab"][aria-selected="false"] {{
            color: {T['text_secondary']};
        }}

        /* [6] Expander */
        [data-testid="stExpander"] {{
            background-color: {T['bg_surface']};
            border: 1px solid {T['border_subtle']};
            border-radius: var(--radius-md);
        }}
        [data-testid="stExpander"] summary {{
            color: {T['text_primary']};
            font-weight: {T['font_weight_semibold']};
        }}

        /* [7] DataFrame */
        .stDataFrame [data-testid="stDataFrameHeader"] {{
            background-color: {T['bg_elevated']};
            color: {T['text_tertiary']};
            font-size: {T['font_size_sm']};
            font-weight: {T['font_weight_semibold']};
        }}
        .stDataFrame [aria-selected="true"] {{
            background-color: {T['bg_elevated']} !important;
            border-left: 3px solid {T['border_strong']};
        }}

        /* [8] Buttons and hit areas */
        .stButton > button {{
            min-height: 36px;
            border-radius: var(--radius-md);
            font-weight: {T['font_weight_medium']};
            transition: background-color var(--motion-fast) {T['easing_standard']}, border-color var(--motion-fast) {T['easing_standard']};
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
        .stButton > button[kind="secondary"],
        [data-testid="baseButton-secondary"],
        [data-testid="baseButton-secondaryFormSubmit"],
        [data-testid="stBaseButton-secondary"],
        [data-testid="stBaseButton-secondaryFormSubmit"] {{
            background-color: var(--button-secondary-bg) !important;
            color: {T['text_primary']} !important;
            border: 1px solid {T['border_default']} !important;
        }}
        .stButton > button[kind="secondary"]:hover,
        [data-testid="baseButton-secondary"]:hover,
        [data-testid="baseButton-secondaryFormSubmit"]:hover,
        [data-testid="stBaseButton-secondary"]:hover,
        [data-testid="stBaseButton-secondaryFormSubmit"]:hover {{
            background-color: var(--button-secondary-hover-bg) !important;
            color: {T['text_primary']} !important;
            border-color: {T['border_strong']} !important;
        }}
        .stButton > button[kind="secondary"] *,
        [data-testid="baseButton-secondary"] *,
        [data-testid="baseButton-secondaryFormSubmit"] *,
        [data-testid="stBaseButton-secondary"] *,
        [data-testid="stBaseButton-secondaryFormSubmit"] * {{
            color: inherit !important;
        }}
        .stButton > button:disabled,
        [data-testid="baseButton-secondary"]:disabled,
        [data-testid="baseButton-secondaryFormSubmit"]:disabled,
        [data-testid="stBaseButton-secondary"]:disabled,
        [data-testid="stBaseButton-secondaryFormSubmit"]:disabled {{
            background-color: var(--button-disabled-bg) !important;
            color: var(--button-disabled-text) !important;
            border-color: {T['border_subtle']} !important;
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
            border-radius: var(--radius-sm);
        }}
        [data-testid="stDataFrame"] thead {{
            z-index: 1;
        }}

        /* [10] Signal classes */
        .signal-buy {{
            color: {T['signal_buy']};
            font-weight: {T['font_weight_semibold']};
        }}
        .signal-sell {{
            color: {T['signal_sell']};
            font-weight: {T['font_weight_semibold']};
        }}
        .signal-none {{
            color: {T['text_tertiary']};
        }}
        .signal-dot {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: var(--space-sm);
            vertical-align: middle;
        }}
        .signal-dot.buy {{ background: {T['signal_buy']}; }}
        .signal-dot.sell {{ background: {T['signal_sell']}; }}
        .signal-dot.none {{ background: {T['text_tertiary']}; }}

        /* [11] Empty state and skeleton */
        .empty-state-icon {{
            width: 36px;
            height: 36px;
            margin: 0 auto 10px;
            color: {T['text_tertiary']};
            opacity: 0.9;
        }}
        .empty-state-icon svg {{
            width: 100%;
            height: 100%;
            fill: none;
            stroke: currentColor;
            stroke-width: 1.8;
            stroke-linecap: round;
            stroke-linejoin: round;
        }}
        .skeleton-block {{
            display: block;
            width: 100%;
            height: var(--skeleton-height, 16px);
            border-radius: var(--radius-md);
            background: linear-gradient(90deg, {T['bg_surface']} 0%, {T['bg_elevated']} 45%, {T['bg_surface']} 90%);
            background-size: 220% 100%;
            animation: skeleton-shimmer 1.2s ease-in-out infinite;
        }}
        @keyframes skeleton-shimmer {{
            0% {{ background-position: 120% 0; }}
            100% {{ background-position: -120% 0; }}
        }}

        /* [12] Screen-reader only utility */
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

        /* [13] Reduced motion */
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
            .skeleton-block {{
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
            [data-testid="baseButton-secondary"],
            [data-testid="stBaseButton-secondary"] {{
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
