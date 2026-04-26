import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config.morandi_palette import BACKGROUND, BORDER, TEXT_PRIMARY, GREEN, RED, GOLD, BLUE


def build_equity_curve(bt_df: pd.DataFrame) -> go.Figure:
    """Cumulative return curve across signal instances."""
    if bt_df.empty:
        return go.Figure()

    bt_df = bt_df.sort_values("date").reset_index(drop=True)
    equity = (1 + bt_df["forward_return_pct"] / 100).cumprod() - 1
    equity_pct = equity * 100

    fig = go.Figure()
    colors = [GREEN if v >= 0 else RED for v in equity_pct]
    fig.add_trace(go.Scatter(
        x=bt_df["date"], y=equity_pct,
        mode="lines+markers",
        line=dict(color=BLUE, width=2),
        marker=dict(color=colors, size=7),
        name="累積報酬",
        hovertemplate="%{x}<br>累積報酬: %{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_color=BORDER, line_width=1)

    fig.update_layout(
        paper_bgcolor=BACKGROUND, plot_bgcolor=BACKGROUND,
        font=dict(color=TEXT_PRIMARY, size=12),
        title=dict(text="Strategy D 累積報酬曲線", font=dict(size=14)),
        xaxis=dict(showgrid=True, gridcolor=BORDER, title="訊號日期"),
        yaxis=dict(showgrid=True, gridcolor=BORDER, title="累積報酬 (%)"),
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
    )
    return fig


def build_return_distribution(bt_df: pd.DataFrame) -> go.Figure:
    """Bar chart of individual signal forward returns."""
    if bt_df.empty:
        return go.Figure()

    bt_df = bt_df.sort_values("date").reset_index(drop=True)
    colors = [GREEN if r >= 0 else RED for r in bt_df["forward_return_pct"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=bt_df["date"],
        y=bt_df["forward_return_pct"],
        marker_color=colors,
        name="各次報酬",
        hovertemplate="%{x}<br>報酬: %{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_color=BORDER, line_width=1)

    fig.update_layout(
        paper_bgcolor=BACKGROUND, plot_bgcolor=BACKGROUND,
        font=dict(color=TEXT_PRIMARY, size=12),
        title=dict(text="各訊號前瞻報酬", font=dict(size=14)),
        xaxis=dict(showgrid=True, gridcolor=BORDER, title="訊號日期"),
        yaxis=dict(showgrid=True, gridcolor=BORDER, title="報酬 (%)"),
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
    )
    return fig
