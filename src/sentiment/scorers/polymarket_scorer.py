from __future__ import annotations

from src.sentiment.scorers.vader import label_for_score
from src.sentiment.sources.polymarket_source import fetch_polymarket_markets, market_to_score


def fetch_polymarket_sentiment(ticker: str) -> dict:  # noqa: ARG001 — ticker-agnostic macro signal
    try:
        markets = fetch_polymarket_markets()
        scored: list[tuple[float, float]] = []
        for market in markets:
            s = market_to_score(market)
            if s is None:
                continue
            vol = float(market.get("volume", 0) or 0)
            scored.append((s, max(vol, 1.0)))

        if not scored:
            return {
                "source": "polymarket",
                "title": "Polymarket",
                "score": 0.0,
                "label": "neutral",
                "count": 0,
                "status": "empty",
                "message": "無相關預測市場",
            }

        total_vol = sum(w for _, w in scored)
        weighted_score = round(sum(s * w for s, w in scored) / total_vol, 4)

        return {
            "source": "polymarket",
            "title": "Polymarket",
            "score": weighted_score,
            "label": label_for_score(weighted_score),
            "count": len(scored),
            "status": "ok",
            "message": "",
        }
    except Exception as exc:
        return {
            "source": "polymarket",
            "title": "Polymarket",
            "score": 0.0,
            "label": "neutral",
            "count": 0,
            "status": "error",
            "message": str(exc)[:80],
        }
