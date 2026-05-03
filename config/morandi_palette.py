BACKGROUND = "#F5F2EE"
SURFACE    = "#EDE9E4"
BORDER     = "#D4CEC8"

TEXT_PRIMARY   = "#4A4540"
TEXT_SECONDARY = "#8A8480"

GREEN  = "#7DAA92"   # 漲 / 買進訊號
RED    = "#C47E7E"   # 跌 / 賣出訊號
BLUE   = "#7A9EB5"   # MACD line
ORANGE = "#C8956C"   # Signal line
PURPLE = "#9B8BB4"   # KD K
BROWN  = "#A89070"   # KD D
GOLD        = "#D4440C"   # Strategy D 買進訊號標記（高對比珊瑚橙紅）
SIGNAL_SELL = "#5B7FA8"   # Strategy D 賣出訊號標記（深湛藍，與買進冷暖對比）

MA_COLORS = {
    5:   "#B5A898",
    10:  "#9A8A7A",
    20:  "#C8956C",
    60:  "#7A9EB5",
    120: "#A07890",
    240: "#6F7E87",
}

PLOTLY_THEME = {
    "paper_bgcolor": BACKGROUND,
    "plot_bgcolor":  BACKGROUND,
    "font":          {"color": TEXT_PRIMARY, "family": "Inter, sans-serif", "size": 12},
    "gridcolor":     BORDER,
}
