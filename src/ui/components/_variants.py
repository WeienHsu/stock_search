from __future__ import annotations

from typing import Literal

StatusVariant = Literal["success", "warning", "danger", "info", "neutral"]
StatusPillSize = Literal["sm", "md"]
LegacyStatusKind = Literal["buy", "sell", "neutral", "warning", "info"]

KpiTone = Literal["up", "down", "neutral"]
KpiSize = Literal["sm", "md", "lg"]

EmptyStateVariant = Literal["default", "compact"]

TableDensity = Literal["compact", "default"]

LEGACY_STATUS_KIND_TO_VARIANT: dict[str, StatusVariant] = {
    "buy": "success",
    "sell": "danger",
    "neutral": "neutral",
    "warning": "warning",
    "info": "info",
}
