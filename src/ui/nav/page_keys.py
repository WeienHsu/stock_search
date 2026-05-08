TODAY = "today"
DASHBOARD = "dashboard"
WORKSTATION = "workstation"
MARKET = "market"
SCANNER = "scanner"
BACKTEST = "backtest"
RISK = "risk"
ALERTS = "alerts"
SETTINGS = "settings"
ADMIN = "admin"

LABEL_BY_KEY = {
    TODAY: "🌅 Today",
    DASHBOARD: "📊 Dashboard",
    WORKSTATION: "🖥️ 綜合看盤",
    MARKET: "🌏 大盤總覽",
    SCANNER: "🔍 掃描器",
    BACKTEST: "🧮 回測",
    RISK: "🛡️ 風控",
    ALERTS: "🔔 警示",
    SETTINGS: "⚙️ 設定",
    ADMIN: "👑 管理",
}

KEY_BY_LABEL = {label: key for key, label in LABEL_BY_KEY.items()}
