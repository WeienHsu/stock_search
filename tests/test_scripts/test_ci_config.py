from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_ci_uses_python_312_and_runs_contrast_check():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert 'python-version: "3.12"' in workflow
    assert "python scripts/check_contrast.py" in workflow


def test_ci_has_manual_a11y_audit_job():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "a11y-audit:" in workflow
    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert "npm install -g @axe-core/cli" in workflow
    assert "python scripts/run_a11y_audit.py --base-url http://localhost:8501" in workflow
    assert "actions/upload-artifact@v4" in workflow


def test_pre_commit_config_includes_contrast_hook():
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "pre-commit-hooks" in config
    assert "check-yaml" in config
    assert "end-of-file-fixer" in config
    assert "trailing-whitespace" in config
    assert "id: contrast-check" in config
    assert "python scripts/check_contrast.py" in config
