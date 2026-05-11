"""Viewport-aware Y-axis fitting JS for Plotly combined charts.

Builds a post-script that listens to plotly_relayout events and re-fits
every Y-axis (price + sub-panels) to the currently visible X range.
"""
from __future__ import annotations

import json


def build_post_script(
    div_id: str,
    dates: list[str],
    lows: list[float | None],
    highs: list[float | None],
    sub_panels: list[dict],
) -> str:
    """Return a JavaScript IIFE post-script for viewport-aware Y-axis fitting.

    Parameters
    ----------
    div_id:
        Plotly chart div ID (same value passed to fig.to_html).
    dates:
        ISO date strings aligned with df rows (for X-range filtering).
    lows / highs:
        Price panel low/high values (None where missing).
    sub_panels:
        List of dicts describing each non-price, non-KD panel:
            {
              "type":        "macd" | "bias" | "volume" | "volume_overlay",
              "axis":        "yaxis2" | "yaxis3" | ...,
              "valueArrays": [[v0, v1, ...], ...],  # one list per series
            }
        KD is intentionally omitted — its [0, 100] range is fixed.
    """
    return f"""
(function() {{
  const gd = document.getElementById({json.dumps(div_id)});
  if (!gd) return;

  const rawDates   = {json.dumps(dates)};
  const priceLows  = {json.dumps(lows)};
  const priceHighs = {json.dumps(highs)};
  const subPanels  = {json.dumps(sub_panels)};

  const xs = rawDates.map(function(d) {{
    const s = String(d);
    const t = Date.parse(s.length > 10 ? s.replace(" ", "T") : s.slice(0, 10) + "T00:00:00");
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
      const end   = Date.parse(r[1]);
      if (Number.isFinite(start) && Number.isFinite(end)) {{
        return [Math.min(start, end), Math.max(start, end)];
      }}
    }}
    return null;
  }}

  function fitAll() {{
    const range = axisRange();
    if (!range) return;

    const updates = {{}};

    // ── Price panel (yaxis) ────────────────────────────────────────────────
    let pLo = Infinity, pHi = -Infinity;
    for (let i = 0; i < xs.length; i++) {{
      const x = xs[i];
      if (x === null || x < range[0] || x > range[1]) continue;
      if (Number.isFinite(priceLows[i]))  pLo = Math.min(pLo, priceLows[i]);
      if (Number.isFinite(priceHighs[i])) pHi = Math.max(pHi, priceHighs[i]);
    }}
    if (Number.isFinite(pLo) && Number.isFinite(pHi)) {{
      let pad = (pHi - pLo) * 0.06;
      if (!Number.isFinite(pad) || pad <= 0) pad = Math.max(Math.abs(pHi) * 0.02, 1);
      updates["yaxis.range"]     = [pLo - pad, pHi + pad];
      updates["yaxis.autorange"] = false;
    }}

    // ── Sub-panels ─────────────────────────────────────────────────────────
    for (const panel of subPanels) {{
      let vMin = Infinity, vMax = -Infinity;
      for (let i = 0; i < xs.length; i++) {{
        const x = xs[i];
        if (x === null || x < range[0] || x > range[1]) continue;
        for (const arr of panel.valueArrays) {{
          const v = arr[i];
          if (v !== null && Number.isFinite(v)) {{
            vMin = Math.min(vMin, v);
            vMax = Math.max(vMax, v);
          }}
        }}
      }}
      if (!Number.isFinite(vMin) || !Number.isFinite(vMax)) continue;

      let lo, hi;
      const t = panel.type;

      if (t === "macd") {{
        const span = vMax - vMin;
        const pad  = Math.max(span * 0.10, Math.abs(vMax) * 0.05, 0.001);
        lo = Math.min(vMin - pad, -pad);   // keep 0 visible
        hi = Math.max(vMax + pad,  pad);
      }} else if (t === "bias") {{
        const abs = Math.max(Math.abs(vMax), Math.abs(vMin)) * 1.15 || 0.01;
        lo = -abs;
        hi =  abs;
      }} else if (t === "volume") {{
        lo = 0;
        hi = vMax * 1.1;
      }} else if (t === "volume_overlay") {{
        lo = 0;
        hi = vMax / 0.22;
      }} else {{
        continue;
      }}

      updates[panel.axis + ".range"]     = [lo, hi];
      updates[panel.axis + ".autorange"] = false;
    }}

    if (Object.keys(updates).length > 0) {{
      Plotly.relayout(gd, updates);
    }}
  }}

  let raf = null;
  function scheduleFit() {{
    if (raf !== null) window.cancelAnimationFrame(raf);
    raf = window.requestAnimationFrame(function() {{
      raf = null;
      fitAll();
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
