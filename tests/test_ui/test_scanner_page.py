from pathlib import Path

from src.ui.pages import scanner_page


def test_scanner_result_table_includes_daily_change_column():
    labels = [column.label for column in scanner_page._result_table_schema()]

    assert "日漲跌" in labels


def test_scanner_sort_options_include_daily_change():
    assert scanner_page._SORT_OPTIONS["日漲跌"] == "daily_change_pct"


def test_scanner_page_uses_empty_state_component():
    source = Path(scanner_page.__file__).read_text(encoding="utf-8")

    assert "render_empty_state" in source
    assert '"自選清單為空"' in source
    assert '"掃描無結果"' in source
