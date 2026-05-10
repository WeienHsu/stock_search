from __future__ import annotations

import re

from src.repositories._backends import get_user_backend

_backend = get_user_backend()
_KEY = "ticker_resolutions"
_SUPPORTED_SUFFIXES = (".TW", ".TWO")


def get_resolved_ticker(ticker: str, user_id: str = "global") -> str | None:
    code = _ticker_code(ticker)
    if not code:
        return None

    suffix = _load(user_id).get(code)
    if suffix not in _SUPPORTED_SUFFIXES:
        return None
    return f"{code}{suffix}"


def save_ticker_resolution(ticker: str, resolved_ticker: str, user_id: str = "global") -> None:
    code = _ticker_code(ticker)
    suffix = _ticker_suffix(resolved_ticker)
    if not code or suffix not in _SUPPORTED_SUFFIXES:
        return

    resolutions = _load(user_id)
    resolutions[code] = suffix
    _backend.save(user_id, _KEY, resolutions)


def clear_ticker_resolutions(user_id: str = "global") -> None:
    _backend.delete(user_id, _KEY)


def _load(user_id: str) -> dict[str, str]:
    saved = _backend.get(user_id, _KEY, default={})
    return saved if isinstance(saved, dict) else {}


def _ticker_code(ticker: str) -> str:
    normalized = str(ticker or "").strip().upper()
    match = re.fullmatch(r"(\d{4,5})(?:\.(?:TW|TWO))?", normalized)
    return match.group(1) if match else ""


def _ticker_suffix(ticker: str) -> str:
    normalized = str(ticker or "").strip().upper()
    for suffix in _SUPPORTED_SUFFIXES:
        if normalized.endswith(suffix):
            return suffix
    return ""
