from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import pandas as pd

from src.data.chip_data_sources.base import ChipDataSource, ChipResult, SourceStatus
from src.data.chip_data_sources.finmind_adapter import FinMindChipDataSource
from src.data.chip_data_sources.tpex_adapter import TpexChipDataSource
from src.data.chip_data_sources.twse_adapter import TwseChipDataSource


@dataclass(slots=True)
class ChipDataChain:
    sources: Sequence[ChipDataSource]

    def fetch_institutional_history(self, ticker: str, days: int) -> ChipResult:
        return self._first_success("fetch_institutional_history", ticker, days)

    def fetch_margin_history(self, ticker: str, days: int) -> ChipResult:
        return self._first_success("fetch_margin_history", ticker, days)

    def fetch_shareholding_snapshot(self, ticker: str) -> ChipResult:
        return self._first_success("fetch_shareholding_snapshot", ticker)

    def fetch_monthly_revenue(self, ticker: str, months: int) -> ChipResult:
        return self._first_success("fetch_monthly_revenue", ticker, months)

    def fetch_total_institutional(self, days: int) -> ChipResult:
        return self._first_success("fetch_total_institutional", days)

    def _first_success(self, method_name: str, *args: Any) -> ChipResult:
        attempts: list[SourceStatus] = []
        fallback: ChipResult | None = None
        for source in self.sources:
            method = getattr(source, method_name, None)
            if method is None:
                continue
            result = method(*args)
            attempts.append(result.source_status)
            if result.source_status.status == "ok" and _has_data(result.data):
                return ChipResult(result.data, result.source_status, attempts=attempts)
            if fallback is None and result.source_status.status in {"unavailable", "unsupported"}:
                fallback = result
        if fallback is not None:
            return ChipResult(fallback.data, fallback.source_status, attempts=attempts)
        return ChipResult(_empty_result(method_name), SourceStatus("chip_chain", "unsupported", "No source available"), attempts=attempts)


def build_default_chain() -> ChipDataChain:
    return ChipDataChain([
        FinMindChipDataSource(),
        TwseChipDataSource(),
        TpexChipDataSource(),
    ])


def _has_data(value: Any) -> bool:
    if isinstance(value, pd.DataFrame):
        return not value.empty
    if isinstance(value, dict):
        if value.get("supported") is False:
            return False
        return bool(value)
    if isinstance(value, list):
        return bool(value)
    return value is not None


def _empty_result(method_name: str) -> Any:
    if "history" in method_name or "revenue" in method_name or "total" in method_name:
        return pd.DataFrame()
    return {}
