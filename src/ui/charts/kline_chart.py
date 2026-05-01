from __future__ import annotations

from dataclasses import dataclass, field
import json

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit.components.v1 as components


@dataclass
class SignalLayer:
    """One strategy's buy/sell markers to overlay on the combined chart."""
    strategy_id: str
    label: str
    buy_dates: list[str] = field(default_factory=list)
    sell_dates: list[str] = field(default_factory=list)
    buy_color: str = "#C8A86A"    # Morandi gold (Strategy D default)
    sell_color: str = "#5B7FA8"   # steel blue (Strategy D default)
    buy_glyph: str = "▼"
    sell_glyph: str = "▲"


def _price_y_range(df: pd.DataFrame, x_start: str | None) -> tuple[float, float] | None:
    """Return a padded [y_min, y_max] from the visible initial window (low/high)."""
    if df.empty:
        return None
    visible = df[df["date"] >= x_start] if x_start and "date" in df.columns else df
    if visible.empty:
        visible = df
    if "low" not in visible.columns or "high" not in visible.columns:
        return None
    y_min, y_max = float(visible["low"].min()), float(visible["high"].max())
    pad = (y_max - y_min) * 0.04
    return y_min - pad, y_max + pad


def _safe_numeric_list(series: pd.Series) -> list[float | None]:
    values = pd.to_numeric(series, errors="coerce")
    return [None if pd.isna(v) else float(v) for v in values]


def _build_rangebreaks(df: pd.DataFrame) -> list[dict]:
    """Return Plotly rangebreaks that skip weekends and market holidays."""
    if df.empty or "date" not in df.columns:
        return []
    try:
        dates = pd.to_datetime(df["date"].astype(str).str[:10])
        min_d, max_d = dates.min(), dates.max()
        all_weekdays = pd.date_range(min_d, max_d, freq="B")  # business days Mon-Fri
        trading_set = set(dates.dt.strftime("%Y-%m-%d"))
        holidays = [d.strftime("%Y-%m-%d") for d in all_weekdays if d.strftime("%Y-%m-%d") not in trading_set]
        breaks: list[dict] = [dict(bounds=["sat", "mon"])]
        if holidays:
            breaks.append(dict(values=holidays))
        return breaks
    except Exception:
        return []


def _get_palette():
    try:
        import streamlit as st
        if st.session_state.get("theme") == "dark":
            import config.dark_palette as P
            return P
    except Exception:
        pass
    import config.morandi_palette as P
    return P


def _apply_layout(fig: go.Figure, title: str = "") -> None:
    P = _get_palette()
    fig.update_layout(
        paper_bgcolor=P.BACKGROUND,
        plot_bgcolor=P.BACKGROUND,
        font=dict(color=P.TEXT_PRIMARY, size=12),
        title=dict(text=title, font=dict(size=15, color=P.TEXT_PRIMARY)),
        legend=dict(bgcolor=P.BACKGROUND, bordercolor=P.BORDER, borderwidth=1, font=dict(size=11)),
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x",
    )
    fig.update_xaxes(
        showgrid=True, gridcolor=P.BORDER, zeroline=False,
        showspikes=True, spikemode="across", spikesnap="cursor",
        spikethickness=1, spikedash="solid", spikecolor="#888",
    )
    fig.update_yaxes(showgrid=True, gridcolor=P.BORDER, zeroline=False)


# ── Trace builders ──

def _main_traces(
    df: pd.DataFrame,
    ticker: str,
    ma_periods: list[int],
) -> list[go.BaseTraceType]:
    P = _get_palette()
    traces: list[go.BaseTraceType] = []
    traces.append(go.Candlestick(
        x=df["date"],
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color=P.GREEN, decreasing_line_color=P.RED,
        name="K線", showlegend=False,
    ))
    for n in sorted(ma_periods):
        col = f"MA_{n}"
        if col in df.columns:
            traces.append(go.Scatter(
                x=df["date"], y=df[col],
                mode="lines", name=f"MA{n}",
                line=dict(color=P.MA_COLORS.get(n, P.TEXT_SECONDARY), width=1.2),
            ))
    return traces


def _signal_traces_below(
    df: pd.DataFrame,
    signal_dates: list[str],
) -> list[go.BaseTraceType]:
    """Signal markers below K-line — used only by standalone build_main_chart."""
    P = _get_palette()
    sig_df = df[df["date"].isin(signal_dates)].copy()
    if sig_df.empty:
        return []
    return [go.Scatter(
        x=sig_df["date"],
        y=sig_df["low"] * 0.985,
        mode="markers",
        marker=dict(symbol="triangle-up", size=15, color=P.GOLD, line=dict(color="#ffffff", width=1)),
        name="Strategy D",
    )]


def _macd_traces(df: pd.DataFrame) -> list[go.BaseTraceType]:
    P = _get_palette()
    colors = [P.GREEN if v >= 0 else P.RED for v in df["histogram"].fillna(0)]
    return [
        go.Bar(x=df["date"], y=df["histogram"], marker_color=colors, name="Histogram", showlegend=False),
        go.Scatter(x=df["date"], y=df["macd_line"], mode="lines", line=dict(color=P.BLUE, width=1.5), name="MACD"),
        go.Scatter(x=df["date"], y=df["signal_line"], mode="lines", line=dict(color=P.ORANGE, width=1.5), name="Signal"),
    ]


def _kd_traces(df: pd.DataFrame) -> list[go.BaseTraceType]:
    P = _get_palette()
    return [
        go.Scatter(x=df["date"], y=df["K"], mode="lines", line=dict(color=P.PURPLE, width=1.5), name="K"),
        go.Scatter(x=df["date"], y=df["D"], mode="lines", line=dict(color=P.BROWN, width=1.5), name="D"),
    ]


def _bias_traces(df: pd.DataFrame, period: int) -> list[go.BaseTraceType]:
    P = _get_palette()
    col = f"bias_{period}"
    if col not in df.columns:
        return []
    colors = [P.GREEN if v >= 0 else P.RED for v in df[col].fillna(0)]
    return [
        go.Bar(x=df["date"], y=df[col], marker_color=colors, name=f"Bias {period}"),
    ]


# ── Combined chart ──

def build_combined_chart(
    df: pd.DataFrame,
    ticker: str,
    ma_periods: list[int],
    signal_dates: list[str],
    bias_period: int,
    show_macd: bool,
    show_kd: bool,
    show_bias: bool,
    x_range_start: str | None = None,
    period: str = "",
    sell_dates: list[str] | None = None,
    uirevision: str = "",
    signal_layers: list[SignalLayer] | None = None,
) -> go.Figure:
    """Combined subplot figure with shared x-axis.

    Always renders full available history; initial view window is set via
    x_range_start so the user can pan/scroll further left into past data.
    The price Y-axis is autoranged by Plotly as the visible X window changes,
    while fixedrange prevents accidental manual Y dragging.
    """
    P = _get_palette()
    sell_dates = sell_dates or []

    panels: list[str] = ["main"]
    if show_macd and "histogram" in df.columns:
        panels.append("macd")
    if show_kd and "K" in df.columns:
        panels.append("kd")
    if show_bias and f"bias_{bias_period}" in df.columns:
        panels.append("bias")

    n_rows = len(panels)
    
    # ── Define ideal pixel heights for each panel type ──
    panel_heights_map = {
        "main": 450,
        "macd": 250,
        "kd": 180,
        "bias": 180,
    }
    raw_heights = [panel_heights_map[p] for p in panels]
    total_height = sum(raw_heights) + 50  # +50 for top/bottom margins
    row_heights = [h / sum(raw_heights) for h in raw_heights]

    panel_titles = {
        "main": f"{ticker} — K 線圖",
        "macd": "MACD",
        "kd": "KD",
        "bias": f"乖離率 (MA{bias_period})",
    }
    fig = make_subplots(
        rows=n_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=[panel_titles[p] for p in panels],
    )

    for row_idx, panel in enumerate(panels, start=1):
        if panel == "main":
            for trace in _main_traces(df, ticker, ma_periods):
                fig.add_trace(trace, row=row_idx, col=1)
        elif panel == "macd":
            for trace in _macd_traces(df):
                fig.add_trace(trace, row=row_idx, col=1)
            fig.add_hline(y=0, line_color=P.BORDER, line_width=1, row=row_idx, col=1)
        elif panel == "kd":
            for trace in _kd_traces(df):
                fig.add_trace(trace, row=row_idx, col=1)
            fig.add_hline(y=80, line_color=P.RED, line_dash="dash", line_width=1, row=row_idx, col=1)
            fig.add_hline(y=20, line_color=P.GREEN, line_dash="dash", line_width=1, row=row_idx, col=1)
            fig.update_yaxes(range=[0, 100], row=row_idx, col=1)
        elif panel == "bias":
            for trace in _bias_traces(df, bias_period):
                fig.add_trace(trace, row=row_idx, col=1)
            fig.add_hline(y=0, line_color=P.BORDER, line_width=1, row=row_idx, col=1)

    date_set = set(df["date"].astype(str)) if not df.empty else set()
    new_annotations = []
    new_shapes = []

    # ── Signal markers: iterate layers (multi-strategy support) ──
    # Fall back to scalar signal_dates / sell_dates when signal_layers not provided.
    if signal_layers is None:
        signal_layers = [SignalLayer(
            strategy_id="strategy_d",
            label="Strategy D",
            buy_dates=list(signal_dates or []),
            sell_dates=list(sell_dates or []),
            buy_color=P.GOLD,
            sell_color=getattr(P, "SIGNAL_SELL", "#5B7FA8"),
        )]

    for layer in signal_layers:
        for sig_date in layer.buy_dates:
            if str(sig_date)[:10] not in date_set:
                continue
            new_annotations.append(dict(
                x=sig_date, y=1.0,
                xref="x", yref="y domain",
                yanchor="top", text=layer.buy_glyph, showarrow=False,
                font=dict(color=layer.buy_color, size=16, family="sans-serif"),
            ))
            new_shapes.append(dict(
                type="line", x0=sig_date, x1=sig_date, y0=0, y1=1,
                xref="x", yref="paper",
                line=dict(color=layer.buy_color, width=1.5, dash="dot"),
                opacity=0.6,
            ))
        for sell_date in layer.sell_dates:
            if str(sell_date)[:10] not in date_set:
                continue
            new_annotations.append(dict(
                x=sell_date, y=0.0,
                xref="x", yref="y domain",
                yanchor="bottom", text=layer.sell_glyph, showarrow=False,
                font=dict(color=layer.sell_color, size=16, family="sans-serif"),
            ))
            new_shapes.append(dict(
                type="line", x0=sell_date, x1=sell_date, y0=0, y1=1,
                xref="x", yref="paper",
                line=dict(color=layer.sell_color, width=1.5, dash="dot"),
                opacity=0.6,
            ))

    if new_annotations or new_shapes:
        fig.update_layout(
            annotations=list(fig.layout.annotations) + new_annotations if fig.layout.annotations else new_annotations,
            shapes=list(fig.layout.shapes) + new_shapes if fig.layout.shapes else new_shapes,
        )

    _apply_layout(fig)
    fig.update_layout(
        height=total_height,
        showlegend=True,
        uirevision=uirevision or f"{ticker}_{period}",
        dragmode="zoom",
    )

    # ── Y-axis: lock manual Y-drag; dashboard renderer updates price Y on X relayout ──
    price_row = panels.index("main") + 1
    price_y = _price_y_range(df, x_range_start)
    if price_y:
        fig.update_yaxes(fixedrange=True, range=list(price_y), row=price_row, col=1)
    else:
        fig.update_yaxes(fixedrange=True, row=price_row, col=1)
    # Sub-panels: lock Y so box-drag stays X-only (their ranges are already set above)
    for i, panel in enumerate(panels, start=1):
        if i != price_row:
            fig.update_yaxes(fixedrange=True, row=i, col=1)

    # ── X-axis: rangebreaks + single rangeslider on the bottom panel only ──
    rangebreaks = _build_rangebreaks(df)
    fig.update_xaxes(rangeslider_visible=False, rangebreaks=rangebreaks)
    if not df.empty:
        fig.update_xaxes(
            rangeslider=dict(
                visible=True,
                thickness=0.04,
                bgcolor=P.SURFACE,
                bordercolor=P.BORDER,
                borderwidth=1,
            ),
            row=n_rows, col=1,
        )

    # ── Set initial X view to selected period window ──
    if x_range_start and not df.empty:
        end_date = df["date"].iloc[-1]
        fig.update_xaxes(range=[x_range_start, end_date], autorange=False)

    return fig


def render_combined_chart(
    fig: go.Figure,
    df: pd.DataFrame,
    key: str,
    config: dict | None = None,
) -> None:
    """Render Plotly chart with client-side price Y fitting on every X relayout."""
    config = {
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        **(config or {}),
    }
    div_id = f"chart_{''.join(ch if ch.isalnum() else '_' for ch in key)}"
    dates = df["date"].astype(str).str[:10].tolist() if "date" in df.columns else []
    lows = _safe_numeric_list(df["low"]) if "low" in df.columns else []
    highs = _safe_numeric_list(df["high"]) if "high" in df.columns else []
    height = int(fig.layout.height or 700) + 20

    post_script = f"""
(function() {{
  const gd = document.getElementById({json.dumps(div_id)});
  if (!gd) return;

  const rawDates = {json.dumps(dates)};
  const lows = {json.dumps(lows)};
  const highs = {json.dumps(highs)};
  const xs = rawDates.map(function(d) {{
    const t = Date.parse(String(d).slice(0, 10) + "T00:00:00");
    return Number.isFinite(t) ? t : null;
  }});

  function axisRange() {{
    const candidates = [];
    [gd.layout, gd._fullLayout].forEach(function(layout) {{
      if (!layout) return;
      ["xaxis"].concat(Object.keys(layout).filter(function(k) {{
        return /^xaxis\\d+$/.test(k);
      }})).forEach(function(axisKey) {{
        if (layout[axisKey] && layout[axisKey].range) {{
          candidates.push(layout[axisKey].range);
        }}
      }});
    }});
    for (const r of candidates) {{
      if (!r || r.length < 2) continue;
      const start = Date.parse(r[0]);
      const end = Date.parse(r[1]);
      if (Number.isFinite(start) && Number.isFinite(end)) {{
        return [Math.min(start, end), Math.max(start, end)];
      }}
    }}
    return null;
  }}

  function fitPriceYAxis() {{
    const range = axisRange();
    if (!range) return;

    let minY = Infinity;
    let maxY = -Infinity;
    for (let i = 0; i < xs.length; i += 1) {{
      const x = xs[i];
      if (x === null || x < range[0] || x > range[1]) continue;
      const lo = lows[i];
      const hi = highs[i];
      if (Number.isFinite(lo)) minY = Math.min(minY, lo);
      if (Number.isFinite(hi)) maxY = Math.max(maxY, hi);
    }}
    if (!Number.isFinite(minY) || !Number.isFinite(maxY)) return;

    let pad = (maxY - minY) * 0.06;
    if (!Number.isFinite(pad) || pad <= 0) {{
      pad = Math.max(Math.abs(maxY) * 0.02, 1);
    }}
    Plotly.relayout(gd, {{
      "yaxis.range": [minY - pad, maxY + pad],
      "yaxis.autorange": false
    }});
  }}

  let raf = null;
  function scheduleFit() {{
    if (raf !== null) window.cancelAnimationFrame(raf);
    raf = window.requestAnimationFrame(function() {{
      raf = null;
      fitPriceYAxis();
    }});
  }}

  gd.on("plotly_relayout", function(eventData) {{
    const keys = Object.keys(eventData || {{}});
    const xChanged = keys.some(function(k) {{
      return /^xaxis\\d*\\.range/.test(k) ||
             /^xaxis\\d*\\.autorange$/.test(k) ||
             /^xaxis\\d*\\.rangeslider/.test(k);
    }});
    if (xChanged) scheduleFit();
  }});
  gd.on("plotly_doubleclick", scheduleFit);
  window.addEventListener("resize", scheduleFit);
  setTimeout(scheduleFit, 100);
}})();
"""
    html = fig.to_html(
        include_plotlyjs="cdn",
        full_html=False,
        div_id=div_id,
        config=config,
        post_script=post_script,
    )
    components.html(html, height=height, scrolling=False)


# ── Standalone chart wrappers (for backtest_page and other callers) ──

def build_main_chart(
    df: pd.DataFrame,
    ticker: str,
    ma_periods: list[int],
    signal_dates: list[str],
) -> go.Figure:
    fig = go.Figure()
    for trace in _main_traces(df, ticker, ma_periods):
        fig.add_trace(trace)
    if signal_dates:
        for trace in _signal_traces_below(df, signal_dates):
            fig.add_trace(trace)
    _apply_layout(fig, title=f"{ticker} — K 線圖")
    fig.update_xaxes(rangeslider_visible=False, rangebreaks=_build_rangebreaks(df))
    return fig


def build_macd_chart(df: pd.DataFrame) -> go.Figure:
    P = _get_palette()
    fig = go.Figure()
    for trace in _macd_traces(df):
        fig.add_trace(trace)
    _apply_layout(fig, title="MACD")
    fig.add_hline(y=0, line_color=P.BORDER, line_width=1)
    return fig


def build_kd_chart(df: pd.DataFrame) -> go.Figure:
    P = _get_palette()
    fig = go.Figure()
    for trace in _kd_traces(df):
        fig.add_trace(trace)
    _apply_layout(fig, title="KD")
    fig.add_hline(y=80, line_color=P.RED,   line_dash="dash", line_width=1, annotation_text="80")
    fig.add_hline(y=20, line_color=P.GREEN, line_dash="dash", line_width=1, annotation_text="20")
    fig.update_yaxes(range=[0, 100])
    return fig


def build_bias_chart(df: pd.DataFrame, period: int) -> go.Figure:
    P = _get_palette()
    col = f"bias_{period}"
    if col not in df.columns:
        return go.Figure()
    fig = go.Figure()
    for trace in _bias_traces(df, period):
        fig.add_trace(trace)
    _apply_layout(fig, title=f"乖離率 (MA{period})")
    fig.add_hline(y=0, line_color=P.BORDER, line_width=1)
    return fig
