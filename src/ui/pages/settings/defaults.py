from __future__ import annotations

import json
from pathlib import Path

_SETTINGS_PATH = Path(__file__).parents[4] / "config" / "default_settings.json"


def load_defaults() -> dict:
    with open(_SETTINGS_PATH, encoding="utf-8") as f:
        return json.load(f)
