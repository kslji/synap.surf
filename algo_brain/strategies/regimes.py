def detect_regime(adx: float, trend: str, atr_pct: float) -> str:
    """
    Determine current market regime based on ADX, Trend, and Volatility.

    STRONG_TREND_UP: High ADX + Up trend
    STRONG_TREND_DOWN: High ADX + Down trend
    WEAK_TREND: Mid ADX
    VOLATILE: High ATR but low ADX (choppy)
    RANGING: Low ADX and low ATR
    """
    if adx >= 25 and trend == "UP":
        return "STRONG_TREND_UP"
    elif adx >= 25 and trend == "DOWN":
        return "STRONG_TREND_DOWN"
    elif 18 <= adx < 25:
        return "WEAK_TREND"
    elif atr_pct > 3.0:
        return "VOLATILE"
    else:
        return "RANGING"
