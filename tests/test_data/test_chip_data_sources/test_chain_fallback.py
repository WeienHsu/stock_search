from datetime import datetime

import pandas as pd

from src.data.chip_data_sources.base import ChipResult, SourceStatus
from src.data.chip_data_sources.chain import ChipDataChain


class DummySource:
    def __init__(self, source_id: str, result: ChipResult):
        self.source_id = source_id
        self._result = result

    def fetch_institutional_history(self, ticker: str, days: int) -> ChipResult:
        return self._result


def test_chain_uses_first_available_success():
    first = DummySource(
        "primary",
        ChipResult(pd.DataFrame(), SourceStatus("primary", "unavailable", reason="down", last_success_at=None, updated_at=datetime.now().timestamp())),
    )
    second = DummySource(
        "fallback",
        ChipResult(pd.DataFrame([{"date": "2026-05-01", "foreign_net_lots": 1.0}]), SourceStatus("fallback", "ok", last_success_at=1.0)),
    )
    chain = ChipDataChain([first, second])

    result = chain.fetch_institutional_history("2330.TW", 5)

    assert result.source_status.source_id == "fallback"
    assert not result.data.empty
    assert len(result.attempts) == 2
