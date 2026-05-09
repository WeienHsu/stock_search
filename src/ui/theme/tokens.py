from typing import Literal

import config.dark_palette as dark_pal
import config.morandi_palette as morandi

ThemeName = Literal["morandi", "dark"]

_FONT_UI = (
    '-apple-system, BlinkMacSystemFont, "PingFang TC", "Microsoft JhengHei", '
    '"Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans TC", sans-serif'
)
_FONT_MONO = (
    '"SF Mono", "JetBrains Mono", "Cascadia Mono", "Roboto Mono", '
    'Menlo, Consolas, "Courier New", monospace'
)

_LIGHT = {
    "bg_base": morandi.BACKGROUND,
    "bg_surface": morandi.SURFACE,
    "bg_elevated": "#E5DFD7",
    "bg_overlay": "rgba(74,69,64,0.45)",
    "border_subtle": "#E0DAD3",
    "border_default": morandi.BORDER,
    "border_strong": morandi.BORDER_STRONG,
    "focus_ring": "#0F4C81",
    "text_primary": morandi.TEXT_PRIMARY,
    "text_secondary": morandi.TEXT_SECONDARY,
    "text_tertiary": morandi.TEXT_TERTIARY,
    "text_disabled": "#A8A29C",
    "text_inverse": "#2B2522",
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
    "chart_blue": "#5985A0",
    "chart_orange": "#A87650",
    "chart_purple": "#7A6A98",
    "chart_brown": "#806A50",
    "chart_slate": "#6F7E87",
    "chart_sand": "#8E8070",
    "chart_rose": "#A07890",
    "chart_green": "#5C8A75",
    "font_ui": _FONT_UI,
    "font_mono": _FONT_MONO,
}

_DARK = {
    "bg_base": dark_pal.BACKGROUND,
    "bg_surface": dark_pal.SURFACE,
    "bg_elevated": "#2E323C",
    "bg_overlay": "rgba(0,0,0,0.55)",
    "border_subtle": "#2F343F",
    "border_default": dark_pal.BORDER,
    "border_strong": dark_pal.BORDER_STRONG,
    "focus_ring": "#8AB4F8",
    "text_primary": dark_pal.TEXT_PRIMARY,
    "text_secondary": dark_pal.TEXT_SECONDARY,
    "text_tertiary": dark_pal.TEXT_TERTIARY,
    "text_disabled": "#525866",
    "text_inverse": "#111418",
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
    "chart_blue": dark_pal.BLUE,
    "chart_orange": dark_pal.ORANGE,
    "chart_purple": dark_pal.PURPLE,
    "chart_brown": dark_pal.BROWN,
    "chart_slate": "#7E8A98",
    "chart_sand": "#8A9AAA",
    "chart_rose": "#C098B0",
    "chart_green": "#6FAA8A",
    "font_ui": _FONT_UI,
    "font_mono": _FONT_MONO,
}


def get_tokens(theme: ThemeName | str = "morandi") -> dict[str, str]:
    return _DARK if theme == "dark" else _LIGHT
