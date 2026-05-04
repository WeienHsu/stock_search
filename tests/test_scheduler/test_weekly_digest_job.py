from dataclasses import dataclass

import pandas as pd

from src.scheduler.jobs import weekly_digest


@dataclass
class SignalStub:
    date: str
    signal_type: str
    strategy_id: str = "strategy_d"


class StrategyStub:
    def default_params(self):
        return {}

    def compute(self, df, params):
        return [SignalStub(str(df["date"].iloc[-1])[:10], "buy")]


def test_build_weekly_digest_rows_calculates_return_and_recent_signal(monkeypatch):
    df = pd.DataFrame({
        "date": pd.date_range("2026-04-27", periods=6, freq="B").strftime("%Y-%m-%d"),
        "open": [100, 101, 102, 103, 104, 105],
        "high": [101, 102, 103, 104, 105, 111],
        "low": [99, 100, 101, 102, 103, 104],
        "close": [100, 101, 102, 103, 104, 110],
        "volume": [1000, 1100, 1200, 1300, 1400, 1500],
    })
    monkeypatch.setattr(weekly_digest, "get_strategy", lambda strategy_id: StrategyStub())
    monkeypatch.setattr(weekly_digest, "fetch_prices_for_strategy", lambda ticker, years=1: df)

    rows = weekly_digest.build_weekly_digest_rows([{"ticker": "tsla", "name": "Tesla"}])

    assert rows[0]["ticker"] == "TSLA"
    assert rows[0]["weekly_return_pct"] == 10.0
    assert "買進" in rows[0]["recent_signals"]


def test_build_weekly_digest_rows_prefers_event_log(monkeypatch):
    df = pd.DataFrame({
        "date": pd.date_range("2026-04-27", periods=6, freq="B").strftime("%Y-%m-%d"),
        "open": [100, 101, 102, 103, 104, 105],
        "high": [101, 102, 103, 104, 105, 111],
        "low": [99, 100, 101, 102, 103, 104],
        "close": [100, 101, 102, 103, 104, 110],
        "volume": [1000, 1100, 1200, 1300, 1400, 1500],
    })

    class NoComputeStrategy(StrategyStub):
        def compute(self, df, params):
            raise AssertionError("weekly digest should use event log")

    monkeypatch.setattr(weekly_digest, "get_strategy", lambda strategy_id: NoComputeStrategy())
    monkeypatch.setattr(weekly_digest, "fetch_prices_for_strategy", lambda ticker, years=1: df)
    monkeypatch.setattr(
        weekly_digest,
        "list_scan_events",
        lambda user_id, since_date=None, strategy_id=None: [
            {
                "ticker": "TSLA",
                "signal_type": "sell",
                "date": "2026-05-01",
                "status": "triggered",
            }
        ],
    )

    rows = weekly_digest.build_weekly_digest_rows([{"ticker": "tsla", "name": "Tesla"}], user_id="user-1")

    assert rows[0]["recent_signals"] == "賣出 2026-05-01"
    assert rows[0]["last_sell_date"] == "2026-05-01"


def test_run_weekly_digest_sends_notification_with_fallback_body(monkeypatch):
    sent = []
    finished = []
    monkeypatch.setattr(weekly_digest, "start_run", lambda job_name: "run-1")
    monkeypatch.setattr(
        weekly_digest,
        "finish_run",
        lambda run_id, status, error=None: finished.append((run_id, status, error)),
    )
    monkeypatch.setattr(weekly_digest, "list_users", lambda: [{"user_id": "user-1"}])
    monkeypatch.setattr(weekly_digest, "get_watchlist", lambda user_id: [{"ticker": "NVDA", "name": "NVIDIA"}])
    monkeypatch.setattr(
        weekly_digest,
        "build_weekly_digest_rows",
        lambda items, user_id=None: [{"ticker": "NVDA", "name": "NVIDIA", "weekly_return_pct": 2.3, "start_close": 100, "current_close": 102.3, "recent_signals": "無"}],
    )
    monkeypatch.setattr(weekly_digest, "build_weekly_digest_body", lambda user_id, rows: ("週報內容", False))
    monkeypatch.setattr(
        weekly_digest,
        "send_notification",
        lambda user_id, subject, body, **kwargs: sent.append((user_id, subject, body, kwargs)) or [],
    )

    result = weekly_digest.run_weekly_digest()

    assert result == {"users_checked": 1, "digests_sent": 1, "ai_generated": 0}
    assert sent[0][1] == "每週投資組合週報"
    assert sent[0][3]["event_type"] == "weekly_digest"
    assert finished == [("run-1", "success", None)]
