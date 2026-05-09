from scripts import profile_fragments


def test_percentile_interpolates_p95():
    assert profile_fragments.percentile([10, 20, 30, 40], 95) == 38.5


def test_run_profile_collects_samples_without_sleep():
    target = profile_fragments.FragmentTarget(
        name="fake_fragment",
        page="Fake",
        run_every_seconds=30,
        workload=lambda ticker: {"ticker": ticker},
        description="fake workload",
    )

    samples = profile_fragments.run_profile(
        [target],
        duration_seconds=600,
        ticker="2330.TW",
        max_samples=2,
        sleep=False,
    )

    assert len(samples) == 2
    assert all(sample.ok for sample in samples)
    assert samples[0].details == {"ticker": "2330.TW"}


def test_build_payload_and_markdown_include_required_metrics():
    samples = [
        profile_fragments.FragmentSample(
            fragment="today_market_strip",
            started_at="2026-05-09T09:00:00+08:00",
            wall_time_ms=10.0,
            ok=True,
            details={"rows": 1},
        ),
        profile_fragments.FragmentSample(
            fragment="today_market_strip",
            started_at="2026-05-09T09:00:30+08:00",
            wall_time_ms=30.0,
            ok=True,
            details={"rows": 2},
        ),
    ]
    target = profile_fragments.FragmentTarget(
        name="today_market_strip",
        page="Today",
        run_every_seconds=30,
        workload=lambda ticker: {},
        description="Today fragment",
    )

    payload = profile_fragments.build_payload(samples, [target], duration_seconds=600, ticker="2330.TW")
    markdown = profile_fragments.render_markdown(payload)

    summary = payload["summaries"]["today_market_strip"]
    assert summary["rerun_count"] == 2
    assert summary["avg_wall_time_ms"] == 20.0
    assert "p95_wall_time_ms" in summary
    assert "| today_market_strip | Today | 30s | 2 |" in markdown


def test_write_artifacts_creates_json_and_markdown(tmp_path):
    payload = {
        "generated_at": "2026-05-09T09:00:00+08:00",
        "duration_seconds": 600,
        "ticker": "2330.TW",
        "method": "test",
        "summaries": {
            "today_market_strip": {
                "page": "Today",
                "run_every_seconds": 30,
                "rerun_count": 1,
                "avg_wall_time_ms": 12.3,
                "p95_wall_time_ms": 12.3,
                "max_wall_time_ms": 12.3,
                "error_count": 0,
            }
        },
        "samples": [],
    }

    json_path, md_path = profile_fragments.write_artifacts(payload, output_dir=tmp_path)

    assert json_path.exists()
    assert md_path.exists()
    assert json_path.name.startswith("fragment_profile_")
    assert "Fragment Profile Summary" in md_path.read_text(encoding="utf-8")
