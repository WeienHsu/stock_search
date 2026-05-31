from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


def fetch_with_source_fallback(
    candidates: Iterable[T],
    fetch_fn: Callable[[T], R],
    is_success: Callable[[R], bool],
    *,
    empty_result: R,
    on_success: Callable[[T, R], None] | None = None,
    on_failure: Callable[[T, str], None] | None = None,
) -> R:
    """Try candidates in order and return the first successful result."""
    for candidate in candidates:
        try:
            result = fetch_fn(candidate)
        except Exception as exc:
            if on_failure is not None:
                on_failure(candidate, str(exc))
            continue

        if is_success(result):
            if on_success is not None:
                on_success(candidate, result)
            return result

        if on_failure is not None:
            on_failure(candidate, "empty response")
    return empty_result
