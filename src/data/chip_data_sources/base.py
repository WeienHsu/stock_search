from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Literal, Protocol, runtime_checkable

SourceState = Literal["ok", "unavailable", "unsupported"]


@dataclass(slots=True)
class SourceStatus:
    source_id: str
    status: SourceState
    reason: str = ""
    last_success_at: float | None = None
    updated_at: float = field(default_factory=time.time)


@dataclass(slots=True)
class ChipResult:
    data: Any
    source_status: SourceStatus
    attempts: list[SourceStatus] = field(default_factory=list)


@runtime_checkable
class ChipDataSource(Protocol):
    source_id: str

    def fetch_institutional_history(self, ticker: str, days: int) -> ChipResult: ...

    def fetch_margin_history(self, ticker: str, days: int) -> ChipResult: ...

    def fetch_shareholding_snapshot(self, ticker: str) -> ChipResult: ...

    def fetch_monthly_revenue(self, ticker: str, months: int) -> ChipResult: ...

    def fetch_total_institutional(self, days: int) -> ChipResult: ...
