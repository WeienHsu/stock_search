import pandas as pd
import plotly.graph_objects as go

from src.ui.theme.plotly_template import apply_chart_theme, get_chart_palette


def build_equity_curve(bt_df: pd.DataFrame) -> go.Figure:
    """Cumulative return curve — x-axis is signal sequence, not calendar date."""
    if bt_df.empty:
        return go.Figure()

    bt_df = bt_df.sort_values("date").reset_index(drop=True)
    equity = (1 + bt_df["forward_return_pct"] / 100).cumprod() - 1
    equity_pct = equity * 100

    x_labels = [f"#{i+1}" for i in range(len(bt_df))]
    hover_text = [
        f"訊號 #{i+1} ({row['date']})<br>前瞻收盤：{row['forward_date']}<br>累積報酬：{v:+.2f}%"
        for i, (v, (_, row)) in enumerate(zip(equity_pct, bt_df.iterrows()))
    ]
    palette = get_chart_palette()
    colors = [palette.MORANDI_UP if v >= 0 else palette.MORANDI_DOWN for v in equity_pct]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_labels,
        y=equity_pct,
        mode="lines+markers",
        line=dict(color=palette.BLUE, width=2),
        marker=dict(color=colors, size=7),
        name="累積報酬",
        text=hover_text,
        hoverinfo="text",
    ))
    fig.add_hline(y=0, line_color=palette.BORDER, line_width=1)

    apply_chart_theme(fig, title="Strategy D 累積報酬曲線（各訊號依序累計）")
    fig.update_layout(
        xaxis=dict(
            showgrid=True, gridcolor=palette.BORDER,
            title="訊號序號",
            type="category",
        ),
        yaxis=dict(showgrid=True, gridcolor=palette.BORDER, title="累積報酬 (%)"),
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
    )
    return fig


def build_return_distribution(bt_df: pd.DataFrame) -> go.Figure:
    """Bar chart of individual signal forward returns — only signal bars, no date gaps."""
    if bt_df.empty:
        return go.Figure()

    bt_df = bt_df.sort_values("date").reset_index(drop=True)
    palette = get_chart_palette()
    colors = [palette.MORANDI_UP if r >= 0 else palette.MORANDI_DOWN for r in bt_df["forward_return_pct"]]

    x_labels = [f"#{i+1}" for i in range(len(bt_df))]
    hover_text = [
        f"訊號 #{i+1}<br>進場日：{row['date']}<br>前瞻日：{row['forward_date']}<br>報酬：{row['forward_return_pct']:+.2f}%"
        for i, (_, row) in enumerate(bt_df.iterrows())
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x_labels,
        y=bt_df["forward_return_pct"],
        marker_color=colors,
        name="各次報酬",
        text=hover_text,
        hoverinfo="text",
    ))
    fig.add_hline(y=0, line_color=palette.BORDER, line_width=1)

    apply_chart_theme(fig, title="各訊號前瞻報酬（僅顯示有買點的直條）")
    fig.update_layout(
        xaxis=dict(
            showgrid=True, gridcolor=palette.BORDER,
            title="訊號序號",
            type="category",
        ),
        yaxis=dict(showgrid=True, gridcolor=palette.BORDER, title="報酬 (%)"),
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
    )
    return fig
