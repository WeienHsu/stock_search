from __future__ import annotations

import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest

pytestmark = pytest.mark.e2e


def test_streamlit_pages_do_not_show_exception(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    port = _free_port()
    base_url = f"http://localhost:{port}"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.headless=true",
            f"--server.port={port}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_server(base_url)
        with playwright.sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as exc:
                pytest.skip(f"Playwright chromium is not installed: {exc}")
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            for name in ["dashboard", "workstation", "market", "settings"]:
                page.goto(f"{base_url}/?page={name}", wait_until="networkidle")
                page.screenshot(path=str(tmp_path / f"{name}.png"), full_page=True)
                assert page.locator("[data-testid='stException']").count() == 0
            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(base_url: str) -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with urlopen(base_url, timeout=2):
                return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Streamlit server did not start: {base_url}")
