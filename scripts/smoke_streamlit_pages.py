from __future__ import annotations

import argparse
import sys
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

PAGE_PARAMS = [
    {},
    {"page": "dashboard"},
    {"page": "workstation"},
    {"page": "market"},
    {"page": "settings"},
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Streamlit pages by HTTP status.")
    parser.add_argument("--base-url", default="http://localhost:8501")
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()

    failures: list[str] = []
    for params in PAGE_PARAMS:
        url = _page_url(args.base_url.rstrip("/"), params)
        try:
            with urlopen(url, timeout=args.timeout) as response:
                status = int(getattr(response, "status", 200))
                response.read(512)
        except URLError as exc:
            failures.append(f"{url} -> {exc}")
            continue
        if status != 200:
            failures.append(f"{url} -> HTTP {status}")
        else:
            print(f"OK {url}")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


def _page_url(base_url: str, params: dict[str, str]) -> str:
    if not params:
        return base_url
    return f"{base_url}/?{urlencode(params)}"


if __name__ == "__main__":
    raise SystemExit(main())
