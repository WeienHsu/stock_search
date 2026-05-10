import pandas as pd

from src.ui.components._variants import LEGACY_STATUS_KIND_TO_VARIANT
from src.ui.components.badge import _resolve_status_variant, _status_pill_size
from src.ui.components.data_table import _row_height_for_density, _style_tone_columns
from src.ui.components.empty_state import _empty_state_layout
from src.ui.components.kpi_card import _delta_direction_from_tone, _kpi_size_tokens


def test_status_pill_variant_aliases_keep_legacy_kind_compatibility():
    assert LEGACY_STATUS_KIND_TO_VARIANT["buy"] == "success"
    assert LEGACY_STATUS_KIND_TO_VARIANT["sell"] == "danger"
    assert _resolve_status_variant("buy", None) == "success"
    assert _resolve_status_variant("sell", None) == "danger"
    assert _resolve_status_variant("buy", "warning") == "warning"
    assert _status_pill_size("md") == ("12px", "4px 10px")


def test_kpi_card_tone_and_size_mappings_are_standardized():
    assert _delta_direction_from_tone("up") == "up"
    assert _delta_direction_from_tone("down") == "down"
    assert _delta_direction_from_tone("neutral") == "flat"
    assert _kpi_size_tokens("sm")["value"] == "20px"
    assert _kpi_size_tokens("lg")["value"] == "30px"


def test_empty_state_variant_layouts_are_distinct():
    assert _empty_state_layout("default")["padding"] == "32px 16px"
    assert _empty_state_layout("compact")["padding"] == "16px 12px"


def test_data_table_density_and_tone_columns_are_supported(monkeypatch):
    import src.ui.utils.styler as styler_module

    monkeypatch.setattr(styler_module, "get_current_theme", lambda: "morandi")

    assert _row_height_for_density("compact") == 28
    assert _row_height_for_density("default") is None

    styled = _style_tone_columns(pd.DataFrame({"change": [1.0, -1.0, 0.0]}), ["change"])

    assert hasattr(styled, "data")
