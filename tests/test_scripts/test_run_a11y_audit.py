import json
from pathlib import Path

from scripts import run_a11y_audit


def test_build_url_and_slug_path():
    assert run_a11y_audit.build_url("http://localhost:8501", "/dashboard") == "http://localhost:8501/dashboard"
    assert run_a11y_audit.slug_path("/") == "root"
    assert run_a11y_audit.slug_path("/dashboard") == "dashboard"


def test_load_violations_supports_axe_list_report(tmp_path):
    report = tmp_path / "axe.json"
    report.write_text(
        json.dumps(
            [
                {
                    "url": "http://localhost:8501",
                    "violations": [
                        {"id": "color-contrast", "impact": "serious", "description": "contrast", "nodes": [{}, {}]}
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    violations = run_a11y_audit.load_violations(report)

    assert violations == [
        {"id": "color-contrast", "impact": "serious", "description": "contrast", "nodes": [{}, {}]}
    ]


def test_build_summary_and_markdown_include_required_sections(tmp_path):
    report = tmp_path / "axe.json"
    report.write_text(
        json.dumps(
            {
                "violations": [
                    {"id": "label", "impact": "critical", "description": "form label", "nodes": [{}]}
                ]
            }
        ),
        encoding="utf-8",
    )
    run = run_a11y_audit.AxeRun(
        url="http://localhost:8501",
        output_path=report,
        returncode=0,
        stdout="",
        stderr="",
    )

    payload = run_a11y_audit.build_summary([run], generated_at="2026-05-09T20:00:00+08:00")
    markdown = run_a11y_audit.render_markdown(payload)

    assert payload["total_pages"] == 1
    assert payload["total_violations"] == 1
    assert payload["audit_error_count"] == 0
    assert payload["pages"][0]["violations"][0]["id"] == "label"
    assert "Accessibility Audit Summary" in markdown
    assert "Audit command errors" in markdown
    assert "Manual Checks Still Required" in markdown


def test_build_summary_marks_missing_axe_report_as_audit_error(tmp_path):
    missing_report = tmp_path / "missing.json"
    run = run_a11y_audit.AxeRun(
        url="http://localhost:8501",
        output_path=missing_report,
        returncode=1,
        stdout="",
        stderr="error: unknown option",
    )

    payload = run_a11y_audit.build_summary([run], generated_at="2026-05-09T20:00:00+08:00")
    markdown = run_a11y_audit.render_markdown(payload)

    assert payload["audit_error_count"] == 1
    assert payload["pages"][0]["audit_error"] is True
    assert "axe error: error: unknown option" in markdown


def test_run_audit_invokes_axe_with_save_report(tmp_path, monkeypatch):
    calls = []

    class Completed:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, capture_output, text, timeout, check):
        calls.append((command, capture_output, text, timeout, check))
        Path(command[command.index("--save") + 1]).write_text('{"violations":[]}', encoding="utf-8")
        return Completed()

    monkeypatch.setattr(run_a11y_audit.subprocess, "run", fake_run)

    runs = run_a11y_audit.run_audit(
        axe_bin="axe",
        base_url="http://localhost:8501",
        paths=["/"],
        output_dir=tmp_path,
        timestamp="20260509_200000",
        timeout=15,
    )

    assert len(runs) == 1
    assert runs[0].output_path.exists()
    command = calls[0][0]
    assert command[:2] == ["axe", "http://localhost:8501/"]
    assert "--save" in command
    assert "--no-reporter" in command
    assert "--reporter" not in command
    assert command[command.index("--timeout") + 1] == "15"
    assert calls[0][3] == 15
