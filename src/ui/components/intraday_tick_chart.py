from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from src.data.price_fetcher import fetch_prices_by_interval


def build_intraday_tick_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = go.Figure()
    if not df.empty and {"date", "close"}.issubset(df.columns):
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["close"],
            mode="lines",
            line=dict(color="#7A9EB5", width=2),
            name="1m",
        ))
    fig.update_layout(
        title=dict(text=f"{ticker} 即時分時", font=dict(size=14)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        height=240,
        hovermode="x unified",
        dragmode="zoom",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#D4CEC8", fixedrange=False)
    fig.update_yaxes(showgrid=True, gridcolor="#D4CEC8", autorange=True, fixedrange=False)
    return fig


def render_intraday_tick_chart(ticker: str, *, key: str | None = None) -> None:
    try:
        df = fetch_prices_by_interval(ticker, "1m", period="1M")
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        st.info("1m 分時資料暫不可用")
        return
    chart_key = key or f"intraday_tick_chart_{ticker}"
    _render_with_y_autofit(build_intraday_tick_chart(df, ticker), df, div_id=chart_key)


def _render_with_y_autofit(fig: go.Figure, df: pd.DataFrame, div_id: str) -> None:
    """Render intraday chart with JS hook: Y-axis auto-fits to visible X range on zoom."""
    dates = df["date"].astype(str).tolist() if "date" in df.columns else []
    closes = [None if pd.isna(v) else float(v) for v in pd.to_numeric(df.get("close", pd.Series()), errors="coerce")] if not df.empty else []

    safe_id = "".join(ch if ch.isalnum() else "_" for ch in div_id)
    post_script = f"""
(function() {{
  const gd = document.getElementById({json.dumps(safe_id)});
  if (!gd) return;

  const rawDates = {json.dumps(dates)};
  const closes = {json.dumps(closes)};
  const xs = rawDates.map(function(d) {{
    const t = Date.parse(String(d));
    return Number.isFinite(t) ? t : null;
  }});

  function fitY() {{
    const layout = gd.layout || {{}};
    const xaxis = gd._fullLayout && gd._fullLayout.xaxis;
    const range = xaxis && xaxis.range;
    if (!range || range.length < 2) return;
    const start = Date.parse(String(range[0]));
    const end = Date.parse(String(range[1]));
    if (!Number.isFinite(start) || !Number.isFinite(end)) return;

    let minY = Infinity, maxY = -Infinity;
    for (let i = 0; i < xs.length; i++) {{
      const x = xs[i];
      if (x === null || x < start || x > end) continue;
      const c = closes[i];
      if (c !== null && Number.isFinite(c)) {{
        if (c < minY) minY = c;
        if (c > maxY) maxY = c;
      }}
    }}
    if (!Number.isFinite(minY) || !Number.isFinite(maxY)) return;
    const pad = (maxY - minY) * 0.08 || Math.abs(maxY) * 0.02 || 1;
    Plotly.relayout(gd, {{"yaxis.range": [minY - pad, maxY + pad], "yaxis.autorange": false}});
  }}

  let raf = null;
  gd.on("plotly_relayout", function(ev) {{
    const keys = Object.keys(ev || {{}});
    const xChanged = keys.some(function(k) {{ return /^xaxis(\\d*\\.range|\\d*\\.autorange)/.test(k); }});
    if (xChanged) {{
      if (raf !== null) window.cancelAnimationFrame(raf);
      raf = window.requestAnimationFrame(function() {{ raf = null; fitY(); }});
    }}
  }});
  gd.on("plotly_doubleclick", function() {{
    Plotly.relayout(gd, {{"yaxis.autorange": true}});
  }});
  setTimeout(fitY, 150);
}})();
"""
    html = fig.to_html(
        include_plotlyjs="cdn",
        full_html=False,
        div_id=safe_id,
        config={"displayModeBar": True, "displaylogo": False, "scrollZoom": True, "responsive": True},
        post_script=post_script,
    )
    components.html(html, height=265, scrolling=False)
