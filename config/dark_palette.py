BACKGROUND = "#1A1D21"
SURFACE    = "#252830"
BORDER     = "#3A3F4B"

TEXT_PRIMARY   = "#E8EAF0"
TEXT_SECONDARY = "#9AA0B0"

GREEN  = "#4CAF82"
RED    = "#E05C5C"
BLUE   = "#5B9BD5"
ORANGE = "#E8A45A"
PURPLE = "#A98ECC"
BROWN  = "#C4A870"
GOLD        = "#FF6B35"   # Strategy D 買進訊號標記（亮橙色，深色背景下高對比）
SIGNAL_SELL = "#8AB4F8"   # Strategy D 賣出訊號標記（亮藍色，深色背景下高對比）

MA_COLORS = {
    5:   "#8A9AAA",
    10:  "#7A8A9A",
    20:  "#E8A45A",
    60:  "#5B9BD5",
    120: "#A87ECC",
}

PLOTLY_THEME = {
    "paper_bgcolor": BACKGROUND,
    "plot_bgcolor":  BACKGROUND,
    "font":          {"color": TEXT_PRIMARY, "family": "Inter, sans-serif", "size": 12},
    "gridcolor":     BORDER,
}
