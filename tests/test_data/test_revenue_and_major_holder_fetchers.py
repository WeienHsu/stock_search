import json

from src.data import major_holder_fetcher, revenue_fetcher


def test_parse_mops_revenue_html_extracts_period_revenue_and_yoy():
    html = """
    <table>
      <tr><th>資料年月</th><th>營業收入淨額</th><th>去年同月增減%</th></tr>
      <tr><td>115/04</td><td>123,456</td><td>12.34</td></tr>
    </table>
    """

    rows = revenue_fetcher.parse_mops_revenue_html(html)

    assert rows[0]["period"] == "2026-04"
    assert rows[0]["revenue"] == 123456
    assert rows[0]["yoy_pct"] == 12.34


def test_major_holder_twse_parser_reads_openapi_record(monkeypatch):
    payload = json.dumps(
        [{"證券代號": "2330", "全體外資及陸資持股比率": "72.34"}],
        ensure_ascii=False,
    )
    monkeypatch.setattr(major_holder_fetcher, "fetch_text", lambda url: payload)

    result = major_holder_fetcher._fetch_twse_foreign_holding("2330")

    assert result["foreign_holding_pct"] == 72.34
    assert result["source"] == "TWSE_MI_QFIIS"


def test_holder_snapshot_to_frame_returns_empty_when_missing_value():
    assert major_holder_fetcher.holder_snapshot_to_frame({"foreign_holding_pct": None}).empty
