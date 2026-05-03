from __future__ import annotations

from typing import Any

import plotly.graph_objects as go


def build_fear_greed_gauge(data: dict[str, Any]) -> go.Figure:
    score = float(data.get("score") or 0)
    rating = str(data.get("rating") or "unavailable").title()
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            title={"text": f"CNN Fear & Greed<br><span style='font-size:0.8em'>{rating}</span>"},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": "#5B7FA8"},
                "steps": [
                    {"range": [0, 30], "color": "rgba(200, 125, 106, 0.28)"},
                    {"range": [30, 70], "color": "rgba(200, 168, 106, 0.25)"},
                    {"range": [70, 100], "color": "rgba(106, 158, 138, 0.28)"},
                ],
                "threshold": {"line": {"color": "#C87D6A", "width": 2}, "value": 30},
            },
        )
    )
    fig.add_trace(
        go.Indicator(
            mode="gauge",
            value=70,
            gauge={
                "axis": {"range": [0, 100], "visible": False},
                "bar": {"color": "rgba(0,0,0,0)"},
                "threshold": {"line": {"color": "#6A9E8A", "width": 2}, "value": 70},
            },
            domain={"x": [0, 1], "y": [0, 1]},
        )
    )
    fig.update_layout(height=280, margin=dict(l=8, r=8, t=40, b=8), showlegend=False)
    return fig
