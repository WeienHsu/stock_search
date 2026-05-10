from __future__ import annotations

from dataclasses import dataclass

import plotly.graph_objects as go

from src.ui.theme import get_current_theme
from src.ui.theme.tokens import get_tokens


@dataclass(frozen=True)
class ChartPalette:
    BACKGROUND: str
    SURFACE: str
    BORDER: str
    BORDER_STRONG: str
    TEXT_PRIMARY: str
    TEXT_SECONDARY: str
    TEXT_TERTIARY: str
    MORANDI_UP: str
    MORANDI_DOWN: str
    SEMANTIC_UP_TEXT: str
    SEMANTIC_DOWN_TEXT: str
    BLUE: str
    ORANGE: str
    PURPLE: str
    BROWN: str
    GOLD: str
    SIGNAL_SELL: str
    GREEN: str
    RED: str
    MA_COLORS: dict[int, str]
    FILL_UP: str
    FILL_DOWN: str
    MARKER_BORDER: str


def get_chart_palette(theme: str | None = None) -> ChartPalette:
    tokens = get_tokens(theme or get_current_theme())
    return ChartPalette(
        BACKGROUND=tokens["bg_base"],
        SURFACE=tokens["bg_surface"],
        BORDER=tokens["chart_grid"],
        BORDER_STRONG=tokens["chart_axis_line"],
        TEXT_PRIMARY=tokens["text_primary"],
        TEXT_SECONDARY=tokens["text_secondary"],
        TEXT_TERTIARY=tokens["text_tertiary"],
        MORANDI_UP=tokens["chart_up"],
        MORANDI_DOWN=tokens["chart_down"],
        SEMANTIC_UP_TEXT=tokens["chart_up_text"],
        SEMANTIC_DOWN_TEXT=tokens["chart_down_text"],
        BLUE=tokens["chart_line_primary"],
        ORANGE=tokens["chart_line_secondary"],
        PURPLE=tokens["chart_purple"],
        BROWN=tokens["chart_brown"],
        GOLD=tokens["chart_signal_buy"],
        SIGNAL_SELL=tokens["chart_signal_sell"],
        GREEN=tokens["chart_down"],
        RED=tokens["chart_up"],
        MA_COLORS={
            5: tokens["chart_ma_5"],
            10: tokens["chart_ma_10"],
            20: tokens["chart_ma_20"],
            60: tokens["chart_ma_60"],
            120: tokens["chart_ma_120"],
            240: tokens["chart_ma_240"],
        },
        FILL_UP=tokens["chart_fill_up"],
        FILL_DOWN=tokens["chart_fill_down"],
        MARKER_BORDER=tokens["chart_marker_border"],
    )


def get_plotly_template(theme: str | None = None) -> dict:
    tokens = get_tokens(theme or get_current_theme())
    return {
        "layout": {
            "paper_bgcolor": tokens["bg_base"],
            "plot_bgcolor": tokens["bg_base"],
            "font": {
                "family": tokens["font_ui"],
                "color": tokens["text_primary"],
                "size": 12,
            },
            "margin": {"l": 55, "r": 20, "t": 40, "b": 10},
            "hovermode": "x",
            "legend": {
                "bgcolor": tokens["bg_base"],
                "bordercolor": tokens["border_default"],
                "borderwidth": 1,
                "font": {"color": tokens["text_secondary"], "size": 11},
            },
            "xaxis": {
                "showgrid": True,
                "gridcolor": tokens["chart_grid"],
                "zeroline": False,
                "showspikes": True,
                "spikemode": "across",
                "spikesnap": "cursor",
                "spikethickness": 1,
                "spikedash": "solid",
                "spikecolor": tokens["chart_axis_line"],
            },
            "yaxis": {
                "showgrid": True,
                "gridcolor": tokens["chart_grid"],
                "zeroline": False,
                "automargin": True,
            },
            "hoverlabel": {
                "bgcolor": tokens["bg_elevated"],
                "bordercolor": tokens["border_default"],
                "font": {
                    "family": tokens["font_mono"],
                    "color": tokens["text_primary"],
                    "size": 12,
                },
            },
            "modebar": {
                "bgcolor": "rgba(0,0,0,0)",
                "color": tokens["text_tertiary"],
                "activecolor": tokens["text_primary"],
            },
        }
    }


def apply_chart_theme(fig: go.Figure, title: str = "", theme: str | None = None) -> go.Figure:
    tokens = get_tokens(theme or get_current_theme())
    layout = get_plotly_template(theme)["layout"]
    fig.update_layout(
        **layout,
        title=dict(text=title, font=dict(size=15, color=tokens["text_primary"])),
    )
    fig.update_xaxes(**layout["xaxis"])
    fig.update_yaxes(**layout["yaxis"])
    return fig
