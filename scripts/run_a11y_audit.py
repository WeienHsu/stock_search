from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.market_calendar import TAIWAN_TZ  # noqa: E402

DEFAULT_PATHS = ["/"]


@dataclass(frozen=True)
class AxeRun:
    url: str
    output_path: Path
    returncode: int
    stdout: str
    stderr: str


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    axe_bin = shutil.which(args.axe_bin)
    if axe_bin is None:
        print(
            f"Missing {args.axe_bin!r}. Install it with: npm install -g @axe-core/cli",
            file=sys.stderr,
        )
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(TAIWAN_TZ).strftime("%Y%m%d_%H%M%S")
    runs = run_audit(
        axe_bin=axe_bin,
        base_url=args.base_url,
        paths=args.path,
        output_dir=output_dir,
        timestamp=timestamp,
        timeout=args.timeout,
    )
    payload = build_summary(runs, generated_at=datetime.now(TAIWAN_TZ).isoformat())
    summary_json = output_dir / f"a11y_audit_{timestamp}.json"
    summary_md = output_dir / f"a11y_audit_{timestamp}.md"
    summary_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_md.write_text(render_markdown(payload), encoding="utf-8")
    print(f"Wrote {summary_json}")
    print(f"Wrote {summary_md}")
    return 1 if payload["total_violations"] else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run axe-core accessibility audit against a running Streamlit app.")
    parser.add_argument("--base-url", default="http://localhost:8501", help="Running Streamlit app base URL.")
    parser.add_argument("--path", action="append", default=None, help="Path to audit. Repeat for multiple paths.")
    parser.add_argument("--output-dir", default="logs", help="Directory for axe JSON and markdown summary.")
    parser.add_argument("--axe-bin", default="axe", help="axe-core CLI executable name or path.")
    parser.add_argument("--timeout", type=int, default=60, help="Per-page axe timeout in seconds.")
    args = parser.parse_args(argv)
    args.path = args.path or DEFAULT_PATHS
    return args


def run_audit(
    *,
    axe_bin: str,
    base_url: str,
    paths: list[str],
    output_dir: Path,
    timestamp: str,
    timeout: int,
) -> list[AxeRun]:
    runs: list[AxeRun] = []
    for path in paths:
        url = build_url(base_url, path)
        output_path = output_dir / f"a11y_axe_{slug_path(path)}_{timestamp}.json"
        command = [
            axe_bin,
            url,
            "--save",
            str(output_path),
            "--no-reporter",
            "--timeout",
            str(timeout),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        runs.append(
            AxeRun(
                url=url,
                output_path=output_path,
                returncode=int(completed.returncode),
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        )
    return runs


def build_summary(runs: list[AxeRun], *, generated_at: str) -> dict:
    pages = []
    total_violations = 0
    audit_error_count = 0
    for run in runs:
        violations = load_violations(run.output_path)
        audit_error = run.returncode != 0 or not run.output_path.exists()
        if audit_error:
            audit_error_count += 1
        total_violations += len(violations)
        pages.append(
            {
                "url": run.url,
                "axe_report": str(run.output_path),
                "returncode": run.returncode,
                "audit_error": audit_error,
                "violation_count": len(violations),
                "violations": [
                    {
                        "id": item.get("id", ""),
                        "impact": item.get("impact", ""),
                        "description": item.get("description", ""),
                        "nodes": len(item.get("nodes", []) or []),
                    }
                    for item in violations
                ],
                "stderr": run.stderr.strip(),
            }
        )
    return {
        "generated_at": generated_at,
        "tool": "axe-core CLI",
        "total_pages": len(pages),
        "total_violations": total_violations,
        "audit_error_count": audit_error_count,
        "pages": pages,
    }


def render_markdown(payload: dict) -> str:
    lines = [
        "# Accessibility Audit Summary",
        "",
        f"- Generated at: {payload['generated_at']}",
        f"- Tool: {payload['tool']}",
        f"- Pages: {payload['total_pages']}",
        f"- Violations: {payload['total_violations']}",
        f"- Audit command errors: {payload['audit_error_count']}",
        "",
        "| URL | Violations | Audit error | Report |",
        "|---|---:|---:|---|",
    ]
    for page in payload["pages"]:
        lines.append(
            f"| {page['url']} | {page['violation_count']} | "
            f"{'yes' if page['audit_error'] else 'no'} | `{page['axe_report']}` |"
        )
        for violation in page["violations"]:
            lines.append(
                f"  - {violation['impact'] or 'unknown'}: {violation['id']} "
                f"({violation['nodes']} nodes) - {violation['description']}"
            )
        if page["audit_error"] and page.get("stderr"):
            lines.append(f"  - axe error: {page['stderr']}")
    lines.extend(
        [
            "",
            "## Manual Checks Still Required",
            "",
            "See `docs/a11y_checklist.md` for VoiceOver/NVDA, color-blind simulation, Lighthouse, and keyboard traversal.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))


def slug_path(path: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in path.strip("/"))
    return slug.strip("_") or "root"


def load_violations(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        if data and isinstance(data[0], dict) and "violations" in data[0]:
            return [violation for page in data for violation in page.get("violations", [])]
        return data
    if isinstance(data, dict):
        return list(data.get("violations", []))
    return []


if __name__ == "__main__":
    raise SystemExit(main())
