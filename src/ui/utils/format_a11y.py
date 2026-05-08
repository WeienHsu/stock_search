from __future__ import annotations


def format_change(value: float, *, unit: str = "%", precision: int = 2) -> dict[str, str]:
    if value > 0:
        text = f"+{value:.{precision}f}{unit}"
        return {"text": text, "icon": "▲", "direction": "up", "aria_label": f"上漲 {text}"}
    if value < 0:
        text = f"−{abs(value):.{precision}f}{unit}"
        return {"text": text, "icon": "▼", "direction": "down", "aria_label": f"下跌 {text}"}
    text = f"0.{''.join(['0'] * precision)}{unit}"
    return {"text": text, "icon": "—", "direction": "flat", "aria_label": "無變化"}


def format_currency(value: float, *, precision: int = 2) -> str:
    if value < 0:
        return f"−{abs(value):,.{precision}f}"
    return f"{value:,.{precision}f}"


def format_percent(value: float, *, precision: int = 2) -> str:
    return format_change(value, unit="%", precision=precision)["text"]
