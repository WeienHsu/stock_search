from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ui.theme.tokens import get_tokens


@dataclass(frozen=True)
class Check:
    name: str
    foreground: str
    background: str
    minimum: float


def main() -> int:
    failures: list[str] = []
    for theme in ("morandi", "dark"):
        tokens = get_tokens(theme)
        checks = [
            Check(f"{theme}: primary text", tokens["text_primary"], tokens["bg_base"], 4.5),
            Check(f"{theme}: secondary text", tokens["text_secondary"], tokens["bg_base"], 4.5),
            Check(f"{theme}: tertiary text", tokens["text_tertiary"], tokens["bg_base"], 3.0),
            Check(f"{theme}: focus ring", tokens["focus_ring"], tokens["bg_base"], 3.0),
            Check(f"{theme}: selected tab text", tokens["tab_selected_text"], tokens["bg_base"], 4.5),
            Check(f"{theme}: sidebar primary text", tokens["text_primary"], tokens["sidebar_bg"], 4.5),
            Check(f"{theme}: sidebar secondary text", tokens["sidebar_text_secondary"], tokens["sidebar_bg"], 4.5),
            Check(f"{theme}: sidebar active nav text", tokens["text_primary"], tokens["sidebar_nav_active_bg"], 4.5),
            Check(f"{theme}: input text", tokens["text_primary"], tokens["control_bg"], 4.5),
            Check(f"{theme}: input placeholder", tokens["text_tertiary"], tokens["control_bg"], 3.0),
            Check(f"{theme}: buy signal text", tokens["semantic_up_text"], tokens["bg_base"], 3.0),
            Check(f"{theme}: sell signal text", tokens["semantic_down_text"], tokens["bg_base"], 3.0),
            Check(f"{theme}: primary button text", tokens["text_inverse"], tokens["signal_buy"], 4.5),
            Check(f"{theme}: secondary button text", tokens["text_primary"], tokens["button_secondary_bg"], 4.5),
            Check(f"{theme}: secondary button hover text", tokens["text_primary"], tokens["button_secondary_hover_bg"], 4.5),
            Check(f"{theme}: disabled button text", tokens["button_disabled_text"], tokens["button_disabled_bg"], 3.0),
        ]
        for check in checks:
            ratio = contrast_ratio(check.foreground, check.background)
            status = "PASS" if ratio >= check.minimum else "FAIL"
            print(f"{status} {check.name}: {ratio:.2f}:1 >= {check.minimum:.1f}:1")
            if ratio < check.minimum:
                failures.append(check.name)
    return 1 if failures else 0


def contrast_ratio(foreground: str, background: str) -> float:
    fg_lum = _relative_luminance(_hex_to_rgb(foreground))
    bg_lum = _relative_luminance(_hex_to_rgb(background))
    lighter = max(fg_lum, bg_lum)
    darker = min(fg_lum, bg_lum)
    return (lighter + 0.05) / (darker + 0.05)


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    text = value.strip().lstrip("#")
    if len(text) != 6:
        raise ValueError(f"Expected 6-digit hex color, got {value!r}")
    return tuple(int(text[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _relative_luminance(rgb: tuple[float, float, float]) -> float:
    channels = []
    for channel in rgb:
        channels.append(channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


if __name__ == "__main__":
    raise SystemExit(main())
