from __future__ import annotations

import json
from typing import Any

import pandas as pd


def build_ohlc_rows(
    df: pd.DataFrame,
    ma_periods: list[int] | None = None,
    ma_colors: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    if df.empty or "date" not in df.columns or "close" not in df.columns:
        return []

    open_values = pd.to_numeric(df.get("open", df["close"]), errors="coerce")
    high_values = pd.to_numeric(df.get("high", df["close"]), errors="coerce")
    low_values = pd.to_numeric(df.get("low", df["close"]), errors="coerce")
    close_values = pd.to_numeric(df["close"], errors="coerce")
    volume_values = pd.to_numeric(df.get("volume", pd.Series([None] * len(df))), errors="coerce")
    ma_columns = [
        (period, pd.to_numeric(df[f"MA_{period}"], errors="coerce"))
        for period in sorted(set(ma_periods or []))
        if f"MA_{period}" in df.columns
    ]

    rows: list[dict[str, Any]] = []
    previous_close: float | None = None
    for idx, raw_date in enumerate(df["date"].astype(str).tolist()):
        open_value = _value_at(open_values, idx)
        high_value = _value_at(high_values, idx)
        low_value = _value_at(low_values, idx)
        close_value = _value_at(close_values, idx)
        volume_value = _value_at(volume_values, idx)
        base = previous_close if previous_close is not None else open_value
        change = close_value - base if close_value is not None and base not in (None, 0) else None
        change_pct = (change / base * 100) if change is not None and base not in (None, 0) else None

        rows.append({
            "key": raw_date,
            "date": raw_date,
            "open": _format_number(open_value),
            "high": _format_number(high_value),
            "low": _format_number(low_value),
            "close": _format_number(close_value),
            "change": _format_signed(change),
            "changePct": _format_signed_pct(change_pct),
            "volume": _format_volume(volume_value),
            "ma": [
                {
                    "label": f"MA{period}",
                    "value": _format_number(_value_at(values, idx)),
                    "color": (ma_colors or {}).get(period, ""),
                }
                for period, values in ma_columns
            ],
            "tone": "up" if change and change > 0 else "down" if change and change < 0 else "neutral",
        })
        if close_value is not None:
            previous_close = close_value
    return rows


def build_ohlc_hover_script(
    div_id: str,
    rows: list[dict[str, str]],
    *,
    up_color: str,
    down_color: str,
    neutral_color: str,
    background_color: str,
    border_color: str,
) -> str:
    return f"""
(function() {{
  const gd = document.getElementById({json.dumps(div_id)});
  if (!gd) return;

  const rows = {json.dumps(rows, ensure_ascii=False)};
  const colors = {{
    up: {json.dumps(up_color)},
    down: {json.dumps(down_color)},
    neutral: {json.dumps(neutral_color)}
  }};
  const byKey = new Map();
  rows.forEach(function(row) {{
    byKey.set(String(row.key), row);
    const dateOnly = String(row.key).slice(0, 10);
    if (!byKey.has(dateOnly)) byKey.set(dateOnly, row);
  }});

  const styleId = {json.dumps(div_id + "__ohlc_style")};
  if (!document.getElementById(styleId)) {{
    const style = document.createElement("style");
    style.id = styleId;
    style.textContent = `
      .stock-ohlc-status {{
        min-height: 58px;
        display: grid;
        grid-template-rows: auto auto;
        row-gap: 4px;
        padding: 7px 10px 8px 10px;
        box-sizing: border-box;
        font: 13px/1.35 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: {neutral_color};
        background: {background_color};
        border-bottom: 1px solid {border_color};
        border-radius: 0;
        opacity: 0;
        visibility: hidden;
        transition: opacity 120ms ease;
        pointer-events: none;
        user-select: none;
      }}
      .stock-ohlc-status.is-visible {{
        opacity: 1;
        visibility: visible;
      }}
      .stock-ohlc-status .stock-ohlc-row {{
        display: flex;
        align-items: center;
        gap: 14px;
        flex-wrap: wrap;
      }}
      .stock-ohlc-status .stock-ohlc-row-ma {{
        gap: 16px;
        font-size: 12px;
      }}
      .stock-ohlc-status span {{
        white-space: nowrap;
        font-variant-numeric: tabular-nums;
      }}
      .stock-ohlc-status .stock-ohlc-date {{
        font-weight: 650;
      }}
      .stock-ohlc-status .stock-ohlc-tone {{
        font-weight: 700;
      }}
      .stock-ohlc-status .stock-ohlc-ma {{
        color: {neutral_color};
        font-weight: 650;
      }}
    `;
    document.head.appendChild(style);
  }}

  const statusId = {json.dumps(div_id + "__ohlc_status")};
  let status = document.getElementById(statusId);
  if (!status) {{
    status = document.createElement("div");
    status.id = statusId;
    status.className = "stock-ohlc-status";
    gd.parentNode.insertBefore(status, gd);
  }}

  function rowForX(x) {{
    if (x === undefined || x === null) return rows[rows.length - 1] || null;
    const raw = String(x).replace("T", " ");
    if (byKey.has(raw)) return byKey.get(raw);
    const dateOnly = raw.slice(0, 10);
    if (byKey.has(dateOnly)) return byKey.get(dateOnly);
    const parsed = Date.parse(String(x));
    if (Number.isFinite(parsed)) {{
      const isoDate = new Date(parsed).toISOString().slice(0, 10);
      if (byKey.has(isoDate)) return byKey.get(isoDate);
    }}
    return rows[rows.length - 1] || null;
  }}

  function addCell(parent, label, value, className) {{
    const span = document.createElement("span");
    if (className) span.className = className;
    span.textContent = label ? label + " " + value : value;
    parent.appendChild(span);
    return span;
  }}

  function render(row) {{
    if (!row) return;
    status.replaceChildren();
    const ohlcRow = document.createElement("div");
    ohlcRow.className = "stock-ohlc-row stock-ohlc-row-main";
    status.appendChild(ohlcRow);
    addCell(ohlcRow, "", row.date, "stock-ohlc-date");
    addCell(ohlcRow, "開", row.open);
    addCell(ohlcRow, "高", row.high);
    addCell(ohlcRow, "低", row.low);
    addCell(ohlcRow, "收", row.close);
    const tone = addCell(ohlcRow, "", row.change + " (" + row.changePct + ")", "stock-ohlc-tone");
    tone.style.color = colors[row.tone] || colors.neutral;
    addCell(ohlcRow, "量", row.volume);
    const maRow = document.createElement("div");
    maRow.className = "stock-ohlc-row stock-ohlc-row-ma";
    status.appendChild(maRow);
    (row.ma || []).forEach(function(item) {{
      const maCell = addCell(maRow, item.label, item.value, "stock-ohlc-ma");
      if (item.color) maCell.style.color = item.color;
    }});
  }}

  function show(row) {{
    render(row);
    status.classList.add("is-visible");
  }}

  function hide() {{
    status.classList.remove("is-visible");
  }}

  gd.on("plotly_hover", function(eventData) {{
    const point = eventData && eventData.points && eventData.points[0];
    show(rowForX(point && point.x));
  }});
  gd.on("plotly_unhover", hide);
  gd.addEventListener("mouseleave", hide);
  render(rows[rows.length - 1] || null);
}})();
"""


def _value_at(values: pd.Series, idx: int) -> float | None:
    try:
        value = values.iloc[idx]
    except IndexError:
        return None
    return None if pd.isna(value) else float(value)


def _format_number(value: float | None) -> str:
    return "—" if value is None else f"{value:,.2f}"


def _format_signed(value: float | None) -> str:
    return "—" if value is None else f"{value:+,.2f}"


def _format_signed_pct(value: float | None) -> str:
    return "—" if value is None else f"{value:+.2f}%"


def _format_volume(value: float | None) -> str:
    return "—" if value is None else f"{value:,.0f}"
