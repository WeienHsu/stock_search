from __future__ import annotations

import pandas as pd
import yfinance as yf

from src.core.market_calendar import cache_ttl_seconds
from src.data.data_source_probe import fetch_text, parse_json_list
from src.data.price_fetcher import _normalize_df
from src.repositories.market_data_cache_repo import get_market_cache, save_market_cache

INDEX_TICKERS = {
    "taiex": "^TWII",
    "gtsm": "^TWOII",
    "usdtwd": "USDTWD=X",
}


def fetch_index_ohlcv(symbol: str, period: str = "3mo") -> pd.DataFrame:
    ticker = INDEX_TICKERS.get(symbol, symbol)
    cache_key = f"index_ohlcv_{ticker}_{period}"
    cached = get_market_cache(
        cache_key,
        ttl_override=cache_ttl_seconds("2330.TW", "intraday" if ticker.startswith("^") else "quote"),
    )
    if isinstance(cached, pd.DataFrame) and not cached.empty:
        return cached

    try:
        raw = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        df = _normalize_df(raw)
        if not df.empty:
            save_market_cache(cache_key, df)
        return df
    except Exception:
        return pd.DataFrame()


def enrich_index_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    from src.indicators.kd import add_kd
    from src.indicators.ma import add_ma
    from src.indicators.macd import add_macd

    enriched = add_ma(df, [5, 10, 20, 60])
    try:
        enriched = add_kd(enriched)
    except ValueError:
        pass
    try:
        enriched = add_macd(enriched)
    except ValueError:
        pass
    return enriched


def index_snapshot(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest
    close = float(latest["close"])
    prev_close = float(prev["close"])
    change_pct = ((close - prev_close) / prev_close * 100) if prev_close else 0.0
    volume = float(latest["volume"]) if "volume" in latest else 0.0
    avg_volume = float(df["volume"].tail(5).mean()) if "volume" in df.columns else 0.0
    return {
        "date": str(latest["date"])[:10],
        "close": close,
        "change_pct": change_pct,
        "kd_status": _kd_status(latest),
        "macd_status": _macd_status(latest),
        "ma_score": ma_alignment_score(df),
        "volume_ratio": (volume / avg_volume) if avg_volume else None,
    }


def get_taiex_realtime_breadth() -> dict:
    cache_key = "realtime_breadth"
    cached = get_market_cache(cache_key, ttl_override=30)
    if isinstance(cached, dict) and cached:
        return cached

    result = _fetch_realtime_breadth()
    save_market_cache(cache_key, result)
    return result


def _fetch_realtime_breadth() -> dict:
    urls = [
        "https://openapi.twse.com.tw/v1/exchangeReport/MI_5MINS",
        "https://openapi.twse.com.tw/v1/exchangeReport/MI_5MINS_INDEX",
    ]
    for url in urls:
        try:
            rows = parse_json_list(fetch_text(url))
            parsed = parse_realtime_breadth_rows(rows)
            if parsed:
                return parsed
        except Exception:
            continue
    return {
        "available": False,
        "buy_orders_lots": 0,
        "sell_orders_lots": 0,
        "buy_sell_diff": 0,
        "ratio": None,
        "ts": "",
        "message": "TWSE 即時委買委賣資料暫不可用",
    }


def parse_realtime_breadth_rows(rows: list[dict]) -> dict:
    if not rows:
        return {}
    latest = rows[-1]
    buy = _first_numeric(latest, ["累積委託買進數量", "CumulativeEntrustedBuyingQuantity", "Cumulative buy order quantity"])
    sell = _first_numeric(latest, ["累積委託賣出數量", "CumulativeEntrustedSellingQuantity", "Cumulative sales order quantity"])
    ts = str(latest.get("時間") or latest.get("Time") or latest.get("time") or "")
    if buy is None or sell is None:
        return {}
    buy = int(buy)
    sell = int(sell)
    return {
        "available": True,
        "buy_orders_lots": buy,
        "sell_orders_lots": sell,
        "buy_sell_diff": buy - sell,
        "ratio": (buy / sell) if sell else None,
        "ts": ts,
        "message": "",
    }


def ma_alignment_score(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    latest = df.iloc[-1]
    periods = [5, 10, 20, 60]
    cols = [f"MA_{period}" for period in periods]
    if any(col not in df.columns or pd.isna(latest.get(col)) for col in cols):
        return 0
    values = [float(latest[col]) for col in cols]
    return sum(1 for idx in range(len(values) - 1) if values[idx] > values[idx + 1]) + 1


def _kd_status(row: pd.Series) -> str:
    k = row.get("K")
    d = row.get("D")
    if pd.isna(k) or pd.isna(d):
        return "資料不足"
    if k >= 80 and d >= 80:
        return "超買"
    if k <= 20 and d <= 20:
        return "超賣"
    return "中性"


def _macd_status(row: pd.Series) -> str:
    hist = row.get("histogram")
    if pd.isna(hist):
        return "資料不足"
    return "多頭" if float(hist) >= 0 else "空頭"


def _first_numeric(row: dict, keys: list[str]) -> float | None:
    for key in keys:
        if key not in row:
            continue
        text = str(row.get(key, "")).replace(",", "").strip()
        if not text:
            continue
        try:
            return float(text)
        except ValueError:
            continue
    return None
