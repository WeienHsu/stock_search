from typing import Literal

import config.dark_palette as dark_pal
import config.morandi_palette as morandi

ThemeName = Literal["morandi", "dark"]
TokenCategory = Literal["colors", "spacing", "typography", "motion"]

_FONT_UI = (
    '-apple-system, BlinkMacSystemFont, "PingFang TC", "Microsoft JhengHei", '
    '"Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans TC", sans-serif'
)
_FONT_MONO = (
    '"SF Mono", "JetBrains Mono", "Cascadia Mono", "Roboto Mono", '
    'Menlo, Consolas, "Courier New", monospace'
)

_SPACING = {
    "space_2xs": "2px",
    "space_xs": "4px",
    "space_sm": "8px",
    "space_md": "12px",
    "space_lg": "16px",
    "space_xl": "24px",
    "space_2xl": "32px",
    "radius_sm": "4px",
    "radius_md": "6px",
    "radius_lg": "8px",
}

_TYPOGRAPHY = {
    "font_ui": _FONT_UI,
    "font_mono": _FONT_MONO,
    "font_size_xs": "11px",
    "font_size_sm": "12px",
    "font_size_md": "13px",
    "font_size_lg": "15px",
    "font_size_xl": "24px",
    "font_weight_regular": "400",
    "font_weight_medium": "500",
    "font_weight_semibold": "600",
}

_MOTION = {
    "motion_fast": "150ms",
    "motion_normal": "240ms",
    "motion_slow": "360ms",
    "easing_standard": "ease",
}

_LIGHT_COLORS = {
    "bg_base": morandi.BACKGROUND,
    "bg_surface": morandi.SURFACE,
    "bg_elevated": "#E5DFD7",
    "bg_overlay": "rgba(74,69,64,0.45)",
    "sidebar_bg": morandi.SURFACE,
    "sidebar_nav_active_bg": "#E5DFD7",
    "control_bg": morandi.SURFACE,
    "control_bg_hover": "#E5DFD7",
    "control_bg_active": "#DED8D0",
    "button_secondary_bg": "#E5DFD7",
    "button_secondary_hover_bg": "#DED8D0",
    "button_disabled_bg": "#E0DAD3",
    "button_disabled_text": "#7C7672",
    "sidebar_text_secondary": "#665F59",
    "border_subtle": "#E0DAD3",
    "border_default": morandi.BORDER,
    "border_strong": morandi.BORDER_STRONG,
    "focus_ring": "#0F4C81",
    "text_primary": morandi.TEXT_PRIMARY,
    "text_secondary": morandi.TEXT_SECONDARY,
    "text_tertiary": morandi.TEXT_TERTIARY,
    "text_disabled": "#A8A29C",
    "text_inverse": "#2B2522",
    "tab_selected_text": "#B03A09",
    "semantic_up": morandi.MORANDI_UP,
    "semantic_up_text": morandi.SEMANTIC_UP_TEXT,
    "semantic_up_soft": "#E8C8C8",
    "semantic_down": morandi.MORANDI_DOWN,
    "semantic_down_text": morandi.SEMANTIC_DOWN_TEXT,
    "semantic_down_soft": "#C8DDD0",
    "semantic_flat": "#7C7672",
    "semantic_warning": morandi.ORANGE,
    "semantic_info": morandi.BLUE,
    "semantic_muted": "#736D68",
    "signal_buy": morandi.MORANDI_UP,
    "signal_sell": morandi.MORANDI_DOWN,
    "signal_neutral": "#7C7672",
    "chart_up": morandi.MORANDI_UP,
    "chart_down": morandi.MORANDI_DOWN,
    "chart_up_text": morandi.SEMANTIC_UP_TEXT,
    "chart_down_text": morandi.SEMANTIC_DOWN_TEXT,
    "chart_signal_buy": morandi.GOLD,
    "chart_signal_sell": morandi.SIGNAL_SELL,
    "chart_grid": morandi.BORDER,
    "chart_axis_line": morandi.BORDER_STRONG,
    "chart_zero_line": morandi.BORDER,
    "chart_blue": "#5985A0",
    "chart_orange": "#A87650",
    "chart_purple": "#7A6A98",
    "chart_brown": "#806A50",
    "chart_slate": "#6F7E87",
    "chart_sand": "#8E8070",
    "chart_rose": "#A07890",
    "chart_green": "#5C8A75",
    "chart_line_primary": "#5985A0",
    "chart_line_secondary": "#A87650",
    "chart_marker_border": "#ffffff",
    "chart_fill_up": "rgba(196,126,126,0.12)",
    "chart_fill_down": "rgba(125,170,146,0.12)",
    "chart_ma_5": "#8E8070",
    "chart_ma_10": "#806A50",
    "chart_ma_20": "#A87650",
    "chart_ma_60": "#5985A0",
    "chart_ma_120": "#A07890",
    "chart_ma_240": "#6F7E87",
}

_DARK_COLORS = {
    "bg_base": dark_pal.BACKGROUND,
    "bg_surface": dark_pal.SURFACE,
    "bg_elevated": "#2E323C",
    "bg_overlay": "rgba(0,0,0,0.55)",
    "sidebar_bg": "#20242C",
    "sidebar_nav_active_bg": "#303642",
    "control_bg": "#2E323C",
    "control_bg_hover": "#363C49",
    "control_bg_active": "#414858",
    "button_secondary_bg": "#303642",
    "button_secondary_hover_bg": "#3A4250",
    "button_disabled_bg": "#252A33",
    "button_disabled_text": "#8A90A0",
    "sidebar_text_secondary": dark_pal.TEXT_SECONDARY,
    "border_subtle": "#2F343F",
    "border_default": dark_pal.BORDER,
    "border_strong": dark_pal.BORDER_STRONG,
    "focus_ring": "#8AB4F8",
    "text_primary": dark_pal.TEXT_PRIMARY,
    "text_secondary": dark_pal.TEXT_SECONDARY,
    "text_tertiary": dark_pal.TEXT_TERTIARY,
    "text_disabled": "#525866",
    "text_inverse": "#111418",
    "tab_selected_text": dark_pal.GOLD,
    "semantic_up": dark_pal.MORANDI_UP,
    "semantic_up_text": dark_pal.SEMANTIC_UP_TEXT,
    "semantic_up_soft": "#3A2828",
    "semantic_down": dark_pal.MORANDI_DOWN,
    "semantic_down_text": dark_pal.SEMANTIC_DOWN_TEXT,
    "semantic_down_soft": "#1F352B",
    "semantic_flat": "#9098A8",
    "semantic_warning": dark_pal.ORANGE,
    "semantic_info": dark_pal.BLUE,
    "semantic_muted": "#8A90A0",
    "signal_buy": dark_pal.MORANDI_UP,
    "signal_sell": dark_pal.MORANDI_DOWN,
    "signal_neutral": "#9098A8",
    "chart_up": dark_pal.MORANDI_UP,
    "chart_down": dark_pal.MORANDI_DOWN,
    "chart_up_text": dark_pal.SEMANTIC_UP_TEXT,
    "chart_down_text": dark_pal.SEMANTIC_DOWN_TEXT,
    "chart_signal_buy": dark_pal.GOLD,
    "chart_signal_sell": dark_pal.SIGNAL_SELL,
    "chart_grid": dark_pal.BORDER,
    "chart_axis_line": dark_pal.BORDER_STRONG,
    "chart_zero_line": dark_pal.BORDER,
    "chart_blue": dark_pal.BLUE,
    "chart_orange": dark_pal.ORANGE,
    "chart_purple": dark_pal.PURPLE,
    "chart_brown": dark_pal.BROWN,
    "chart_slate": "#7E8A98",
    "chart_sand": "#8A9AAA",
    "chart_rose": "#C098B0",
    "chart_green": "#6FAA8A",
    "chart_line_primary": dark_pal.BLUE,
    "chart_line_secondary": dark_pal.ORANGE,
    "chart_marker_border": dark_pal.BACKGROUND,
    "chart_fill_up": "rgba(232,88,32,0.14)",
    "chart_fill_down": "rgba(76,175,130,0.14)",
    "chart_ma_5": "#8A9AAA",
    "chart_ma_10": "#7A8A9A",
    "chart_ma_20": "#E8A45A",
    "chart_ma_60": "#5B9BD5",
    "chart_ma_120": "#A87ECC",
    "chart_ma_240": "#7E8A98",
}

_LIGHT = {**_LIGHT_COLORS, **_SPACING, **_TYPOGRAPHY, **_MOTION}
_DARK = {**_DARK_COLORS, **_SPACING, **_TYPOGRAPHY, **_MOTION}

COLOR_TOKEN_KEYS = tuple(_LIGHT_COLORS.keys())
SPACING_TOKEN_KEYS = tuple(_SPACING.keys())
TYPOGRAPHY_TOKEN_KEYS = tuple(_TYPOGRAPHY.keys())
MOTION_TOKEN_KEYS = tuple(_MOTION.keys())
TOKEN_REGISTRY_KEYS: dict[TokenCategory, tuple[str, ...]] = {
    "colors": COLOR_TOKEN_KEYS,
    "spacing": SPACING_TOKEN_KEYS,
    "typography": TYPOGRAPHY_TOKEN_KEYS,
    "motion": MOTION_TOKEN_KEYS,
}


def get_tokens(theme: ThemeName | str = "morandi") -> dict[str, str]:
    return _DARK if theme == "dark" else _LIGHT


def get_token_registry(theme: ThemeName | str = "morandi") -> dict[TokenCategory, dict[str, str]]:
    tokens = get_tokens(theme)
    return {
        category: {key: tokens[key] for key in keys}
        for category, keys in TOKEN_REGISTRY_KEYS.items()
    }
