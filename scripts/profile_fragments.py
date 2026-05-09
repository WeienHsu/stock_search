from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.market_calendar import TAIWAN_TZ  # noqa: E402
from src.data.index_fetcher import enrich_index_indicators, fetch_index_ohlcv, get_taiex_realtime_breadth  # noqa: E402
from src.data.price_fetcher import fetch_prices_by_interval  # noqa: E402
from src.ui.components.intraday_tick_chart import build_intraday_tick_chart  # noqa: E402

Workload = Callable[[str], dict[str, Any]]


@dataclass(frozen=True)
class FragmentTarget:
    name: str
    page: str
    run_every_seconds: int
    workload: Workload
    description: str


@dataclass
class FragmentSample:
    fragment: str
    started_at: str
    wall_time_ms: float
    ok: bool
    details: dict[str, Any]
    error: str = ""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.no_sleep and args.max_samples is None:
        raise SystemExit("--no-sleep requires --max-samples to avoid a busy loop.")
    targets = default_targets()
    samples = run_profile(
        targets,
        duration_seconds=args.duration,
        ticker=args.ticker,
        max_samples=args.max_samples,
        sleep=not args.no_sleep,
    )
    payload = build_payload(samples, targets, duration_seconds=args.duration, ticker=args.ticker)
    json_path, md_path = write_artifacts(payload, output_dir=args.output_dir)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile Streamlit fragment data workloads.")
    parser.add_argument("--duration", type=int, default=600, help="Profiling window in seconds.")
    parser.add_argument("--ticker", default="2330.TW", help="Ticker used for Workstation intraday profiling.")
    parser.add_argument("--output-dir", type=Path, default=Path("logs"), help="Directory for JSON and markdown outputs.")
    parser.add_argument("--max-samples", type=int, default=None, help="Stop after N samples per fragment.")
    parser.add_argument("--no-sleep", action="store_true", help="Run scheduled samples immediately; useful for smoke tests.")
    return parser.parse_args(argv)


def default_targets() -> list[FragmentTarget]:
    return [
        FragmentTarget(
            name="today_market_strip",
            page="Today",
            run_every_seconds=30,
            workload=profile_today_market_strip,
            description="Approximates Today _render_market_strip_fragment by profiling its data loaders.",
        ),
        FragmentTarget(
            name="workstation_intraday",
            page="Workstation",
            run_every_seconds=60,
            workload=profile_workstation_intraday,
            description="Approximates Workstation _render_intraday_fragment by fetching 1m data and building the figure.",
        ),
    ]


def run_profile(
    targets: list[FragmentTarget],
    *,
    duration_seconds: int,
    ticker: str,
    max_samples: int | None = None,
    sleep: bool = True,
) -> list[FragmentSample]:
    if duration_seconds < 0:
        raise ValueError("duration_seconds must be >= 0")
    if max_samples is not None and max_samples <= 0:
        raise ValueError("max_samples must be positive")

    start = time.monotonic()
    next_due = {target.name: start for target in targets}
    counts = {target.name: 0 for target in targets}
    samples: list[FragmentSample] = []

    while True:
        now = time.monotonic()
        if _profile_complete(now, start, duration_seconds, counts, max_samples):
            break

        due_targets = [
            target
            for target in targets
            if now >= next_due[target.name] and (max_samples is None or counts[target.name] < max_samples)
        ]
        if not due_targets:
            if not sleep:
                next_due = {
                    name: min(due_at, now)
                    for name, due_at in next_due.items()
                }
                continue
            time.sleep(max(0.05, min(next_due.values()) - now))
            continue

        for target in due_targets:
            samples.append(_run_one_sample(target, ticker))
            counts[target.name] += 1
            next_due[target.name] = time.monotonic() + target.run_every_seconds

    return samples


def profile_today_market_strip(_ticker: str) -> dict[str, Any]:
    taiex = enrich_index_indicators(fetch_index_ohlcv("taiex", "1mo"))
    gtsm = enrich_index_indicators(fetch_index_ohlcv("gtsm", "1mo"))
    breadth = get_taiex_realtime_breadth()
    return {
        "taiex_rows": int(len(taiex)),
        "gtsm_rows": int(len(gtsm)),
        "breadth_available": bool(breadth.get("available")) if isinstance(breadth, dict) else False,
    }


def profile_workstation_intraday(ticker: str) -> dict[str, Any]:
    df = fetch_prices_by_interval(ticker, "1m", period="1M")
    fig = build_intraday_tick_chart(df, ticker)
    return {
        "ticker": ticker,
        "rows": int(len(df)),
        "traces": int(len(fig.data)),
        "empty": bool(df.empty),
    }


def build_payload(
    samples: list[FragmentSample],
    targets: list[FragmentTarget],
    *,
    duration_seconds: int,
    ticker: str,
) -> dict[str, Any]:
    summaries = {}
    for target in targets:
        target_samples = [sample for sample in samples if sample.fragment == target.name]
        summaries[target.name] = {
            "page": target.page,
            "run_every_seconds": target.run_every_seconds,
            "description": target.description,
            **summarize_samples(target_samples),
        }
    return {
        "generated_at": datetime.now(TAIWAN_TZ).isoformat(),
        "timezone": "Asia/Taipei",
        "duration_seconds": duration_seconds,
        "ticker": ticker,
        "method": "CLI approximation of fragment data workloads; Streamlit DOM/render cost is not included.",
        "summaries": summaries,
        "samples": [asdict(sample) for sample in samples],
    }


def summarize_samples(samples: list[FragmentSample]) -> dict[str, Any]:
    wall_times = [sample.wall_time_ms for sample in samples]
    ok_count = sum(1 for sample in samples if sample.ok)
    return {
        "rerun_count": len(samples),
        "ok_count": ok_count,
        "error_count": len(samples) - ok_count,
        "avg_wall_time_ms": round(sum(wall_times) / len(wall_times), 2) if wall_times else 0.0,
        "p95_wall_time_ms": round(percentile(wall_times, 95), 2) if wall_times else 0.0,
        "max_wall_time_ms": round(max(wall_times), 2) if wall_times else 0.0,
    }


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct / 100
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def write_artifacts(payload: dict[str, Any], *, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(TAIWAN_TZ).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"fragment_profile_{timestamp}.json"
    md_path = output_dir / f"fragment_profile_{timestamp}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return json_path, md_path


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Fragment Profile Summary",
        "",
        f"- Generated at: {payload['generated_at']}",
        f"- Duration: {payload['duration_seconds']}s",
        f"- Ticker: {payload['ticker']}",
        f"- Method: {payload['method']}",
        "",
        "| Fragment | Page | run_every | reruns | avg ms | p95 ms | max ms | errors |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, summary in payload["summaries"].items():
        lines.append(
            "| "
            f"{name} | {summary['page']} | {summary['run_every_seconds']}s | "
            f"{summary['rerun_count']} | {summary['avg_wall_time_ms']:.2f} | "
            f"{summary['p95_wall_time_ms']:.2f} | {summary['max_wall_time_ms']:.2f} | "
            f"{summary['error_count']} |"
        )
    lines.extend(["", "## Notes", "", "- Streamlit browser rendering and websocket overhead are not included."])
    return "\n".join(lines) + "\n"


def _run_one_sample(target: FragmentTarget, ticker: str) -> FragmentSample:
    started_at = datetime.now(TAIWAN_TZ).isoformat()
    start = time.perf_counter()
    try:
        details = target.workload(ticker)
        return FragmentSample(
            fragment=target.name,
            started_at=started_at,
            wall_time_ms=round((time.perf_counter() - start) * 1000, 2),
            ok=True,
            details=details,
        )
    except Exception as exc:
        return FragmentSample(
            fragment=target.name,
            started_at=started_at,
            wall_time_ms=round((time.perf_counter() - start) * 1000, 2),
            ok=False,
            details={},
            error=f"{type(exc).__name__}: {exc}",
        )


def _profile_complete(
    now: float,
    start: float,
    duration_seconds: int,
    counts: dict[str, int],
    max_samples: int | None,
) -> bool:
    duration_done = (now - start) >= duration_seconds
    samples_done = max_samples is not None and all(count >= max_samples for count in counts.values())
    return duration_done or samples_done


if __name__ == "__main__":
    raise SystemExit(main())
