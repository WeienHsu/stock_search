from pathlib import Path


def test_skeleton_helper_exists():
    source = Path("src/ui/components/skeleton.py").read_text()

    assert "skeleton-block" in source
    assert "data-testid" in source


def test_skeleton_css_respects_reduced_motion():
    source = Path("src/ui/theme/styles.py").read_text()

    assert ".skeleton-block" in source
    assert "skeleton-shimmer" in source
    assert "@media (prefers-reduced-motion: reduce)" in source
