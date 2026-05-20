import pandas as pd
import numpy as np
from typing import Dict, Any
from . import indicators
from . import regimes

def calculate_all(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Main entry point for calculating all technical indicators and 
    market regimes for a given OHLC DataFrame.
    """
    if df is None or len(df) < 50:
        return {"error": "Not enough data"}

    close = df["close"].values.astype(float)
    high = df["high"].values.astype(float)
    low = df["low"].values.astype(float)
    n = len(close)

    result = {}

    # ── Price info ───────────────────────────────────────────────────
    result["current_price"] = round(float(close[-1]), 6)
    result["price_change_24h_pct"] = round(
        (close[-1] / close[max(0, n - 48)] - 1) * 100, 2
    ) if n >= 48 else 0.0
    result["price_change_7d_pct"] = round(
        (close[-1] / close[max(0, n - 336)] - 1) * 100, 2
    ) if n >= 336 else 0.0

    # ── Individual Indicators ────────────────────────────────────────
    result["rsi_14"] = indicators.compute_rsi(close)
    result.update(indicators.compute_macd(close))
    result.update(indicators.compute_bollinger_bands(close))
    
    atr_data = indicators.compute_atr(high, low, close)
    result.update(atr_data)
    
    ema20 = indicators.compute_ema(close, 20)
    ema50 = indicators.compute_ema(close, 50)
    result["ema_20"] = ema20
    result["ema_50"] = ema50
    result["trend"] = "UP" if ema20 > ema50 * 1.001 else (
        "DOWN" if ema20 < ema50 * 0.999 else "FLAT"
    )

    # ── Volume analysis ──────────────────────────────────────────────
    vol = df["volume"].values.astype(float)
    avg_vol_20 = float(np.mean(vol[-20:]))
    current_vol = float(vol[-1])
    volume_ratio = round(current_vol / (avg_vol_20 + 1e-10), 2)
    result["volume_ratio"] = volume_ratio
    result["volume_trend"] = "HIGH" if volume_ratio > 1.5 else (
        "LOW" if volume_ratio < 0.5 else "NORMAL"
    )

    # ── ADX & Regime ──────────────────────────────────────────────
    adx = indicators.compute_adx(df)
    result["adx"] = round(adx, 2)
    result["regime"] = regimes.detect_regime(adx, result["trend"], atr_data.get("atr_pct", 0))

    # ── Support / Resistance ────────────────────────────────────────
    recent_high = float(np.max(high[-20:]))
    recent_low = float(np.min(low[-20:]))
    pivot = (recent_high + recent_low + close[-1]) / 3
    result["support_1"] = round(2 * pivot - recent_high, 6)
    result["resistance_1"] = round(2 * pivot - recent_low, 6)
    result["pivot"] = round(pivot, 6)

    return result
