from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_ci_runs_pytest_on_python_312():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert 'python-version: "3.12"' in workflow
    assert "pytest -q" in workflow


def test_ci_builds_web_frontend():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "web-build:" in workflow
    assert 'node-version: "22"' in workflow
    assert "npm run build" in workflow
    assert "working-directory: web" in workflow


def test_pre_commit_config_includes_basic_hooks():
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "pre-commit-hooks" in config
    assert "check-yaml" in config
    assert "end-of-file-fixer" in config
