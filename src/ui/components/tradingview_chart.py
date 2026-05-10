from __future__ import annotations

from urllib.parse import urlencode

import streamlit as st

from src.data.exchange_mapper import ticker_to_tv_symbol

_TV_WIDGET_BASE = "https://s.tradingview.com/widgetembed/"


def _build_widget_url(symbol: str, *, theme: str = "light", interval: str = "D") -> str:
    params = {
        "symbol": symbol,
        "interval": interval,
        "theme": theme,
        "style": "1",
        "locale": "zh_TW",
        "timezone": "Asia/Taipei",
        "allow_symbol_change": "false",
        "hide_side_toolbar": "0",
        "save_image": "1",
    }
    return f"{_TV_WIDGET_BASE}?{urlencode(params)}"


def render_tradingview_chart(ticker: str, *, height: int = 620, theme: str = "light") -> None:
    symbol = ticker_to_tv_symbol(ticker)
    url = _build_widget_url(symbol, theme=theme)
    st.caption(f"TradingView · {symbol}　資料來源：[TradingView](https://www.tradingview.com)")
    st.iframe(url, height=height)
