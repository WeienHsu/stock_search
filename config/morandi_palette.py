BACKGROUND = "#F5F2EE"
SURFACE    = "#EDE9E4"
BORDER     = "#D4CEC8"
BORDER_STRONG = "#8A7E76"

TEXT_PRIMARY   = "#4A4540"
TEXT_SECONDARY = "#736D68"
TEXT_TERTIARY  = "#7C7672"

GREEN  = "#7DAA92"   # 跌 / 賣出訊號
RED    = "#C47E7E"   # 漲 / 買進訊號
SEMANTIC_UP_TEXT   = "#9E5252"
SEMANTIC_DOWN_TEXT = "#4D7868"
BLUE   = "#7A9EB5"   # MACD line
ORANGE = "#C8956C"   # Signal line
PURPLE = "#9B8BB4"   # KD K
BROWN  = "#A89070"   # KD D
GOLD        = "#D4440C"   # Strategy D 買進訊號標記（高對比珊瑚橙紅）
SIGNAL_SELL = "#5B7FA8"   # Strategy D 賣出訊號標記（深湛藍，與買進冷暖對比）

MA_COLORS = {
    5:   "#8E8070",
    10:  "#806A50",
    20:  "#A87650",
    60:  "#5985A0",
    120: "#A07890",
    240: "#6F7E87",
}

PLOTLY_THEME = {
    "paper_bgcolor": BACKGROUND,
    "plot_bgcolor":  BACKGROUND,
    "font":          {"color": TEXT_PRIMARY, "family": '-apple-system, "PingFang TC", "Microsoft JhengHei", Inter, sans-serif', "size": 12},
    "gridcolor":     BORDER,
}
