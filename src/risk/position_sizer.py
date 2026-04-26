def compute_position_size(
    portfolio_size: float,
    max_risk_pct: float,
    risk_per_share: float,
    entry_price: float,
) -> dict:
    """
    Calculate suggested position size based on fixed fractional risk.

    max_risk_pct: percentage of portfolio to risk on this trade (e.g. 1.0 = 1%)
    risk_per_share: entry_price - stop_price

    Returns: shares, position_value, actual_risk_amount
    """
    if risk_per_share <= 0:
        return {"shares": 0, "position_value": 0.0, "actual_risk_amount": 0.0}

    risk_amount = portfolio_size * max_risk_pct / 100
    shares = int(risk_amount / risk_per_share)
    position_value = shares * entry_price
    actual_risk = shares * risk_per_share

    return {
        "shares": shares,
        "position_value": round(position_value, 2),
        "actual_risk_amount": round(actual_risk, 2),
        "position_pct": round(position_value / portfolio_size * 100, 1) if portfolio_size > 0 else 0.0,
    }
