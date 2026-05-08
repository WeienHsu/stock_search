from __future__ import annotations

from typing import Literal

_ARIA_LABELS = {
    "buy": "買進訊號",
    "sell": "賣出訊號",
    "none": "無訊號",
}


def signal_dot_html(state: Literal["buy", "sell", "none"]) -> str:
    label = _ARIA_LABELS[state]
    return f'<span class="signal-dot {state}" role="img" aria-label="{label}"></span>'
