from __future__ import annotations

import plotly.graph_objects as go

from src.ui.theme import get_current_theme
from src.ui.theme.tokens import get_tokens


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
                "gridcolor": tokens["border_default"],
                "zeroline": False,
                "showspikes": True,
                "spikemode": "across",
                "spikesnap": "cursor",
                "spikethickness": 1,
                "spikedash": "solid",
                "spikecolor": tokens["border_strong"],
            },
            "yaxis": {
                "showgrid": True,
                "gridcolor": tokens["border_default"],
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
