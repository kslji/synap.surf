import numpy as np
import pandas as pd
from typing import Dict, Any

def compute_rsi(close: np.ndarray, period: int = 14) -> float:
    """Compute Relative Strength Index."""
    try:
        delta = np.diff(close)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = pd.Series(gain).ewm(span=period, adjust=False).mean().iloc[-1]
        avg_loss = pd.Series(loss).ewm(span=period, adjust=False).mean().iloc[-1]
        rs = avg_gain / (avg_loss + 1e-10)
        return round(100 - 100 / (1 + rs), 2)
    except Exception:
        return 50.0

def compute_macd(close: np.ndarray) -> Dict[str, Any]:
    """Compute MACD, Signal line and Histogram."""
    try:
        ema12 = pd.Series(close).ewm(span=12, adjust=False).mean()
        ema26 = pd.Series(close).ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        return {
            "macd": round(float(macd_line.iloc[-1]), 6),
            "macd_signal": round(float(signal_line.iloc[-1]), 6),
            "macd_histogram": round(float(macd_line.iloc[-1] - signal_line.iloc[-1]), 6),
            "macd_cross": "BULLISH" if macd_line.iloc[-1] > signal_line.iloc[-1] and macd_line.iloc[-2] <= signal_line.iloc[-2] else (
                "BEARISH" if macd_line.iloc[-1] < signal_line.iloc[-1] and macd_line.iloc[-2] >= signal_line.iloc[-2] else "NONE"
            )
        }
    except Exception:
        return {"macd": 0.0, "macd_signal": 0.0, "macd_histogram": 0.0, "macd_cross": "NONE"}

def compute_bollinger_bands(close: np.ndarray, period: int = 20) -> Dict[str, Any]:
    """Compute Bollinger Bands."""
    try:
        sma = pd.Series(close).rolling(period).mean().iloc[-1]
        std = pd.Series(close).rolling(period).std().iloc[-1]
        upper = sma + 2 * std
        lower = sma - 2 * std
        bb_pct = (close[-1] - lower) / (upper - lower + 1e-10)
        return {
            "bb_upper": round(float(upper), 6),
            "bb_lower": round(float(lower), 6),
            "bb_pct_b": round(float(bb_pct), 4)
        }
    except Exception:
        return {"bb_upper": 0.0, "bb_lower": 0.0, "bb_pct_b": 0.5}

def compute_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> Dict[str, Any]:
    """Compute Average True Range."""
    try:
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1]))
        )
        atr = float(np.mean(tr[-period:]))
        return {
            "atr_14": round(atr, 6),
            "atr_pct": round(atr / close[-1] * 100, 3)
        }
    except Exception:
        return {"atr_14": 0.0, "atr_pct": 0.0}

def compute_ema(close: np.ndarray, span: int) -> float:
    """Compute Exponential Moving Average."""
    try:
        return round(float(pd.Series(close).ewm(span=span, adjust=False).mean().iloc[-1]), 6)
    except Exception:
        return 0.0

def compute_adx(df: pd.DataFrame, period: int = 14) -> float:
    """Compute Average Directional Index."""
    try:
        hi = np.array(df["high"], dtype=np.float64)
        lo = np.array(df["low"], dtype=np.float64)
        cl = np.array(df["close"], dtype=np.float64)
        n = len(hi)
        if n < period * 2 + 1:
            return 0.0

        tr = np.zeros(n)
        tr[1:] = np.maximum(
            hi[1:] - lo[1:],
            np.maximum(np.abs(hi[1:] - cl[:-1]), np.abs(lo[1:] - cl[:-1]))
        )
        up_move = hi[1:] - hi[:-1]
        down_move = lo[:-1] - lo[1:]
        plus_dm = np.zeros(n)
        minus_dm = np.zeros(n)
        plus_dm[1:] = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm[1:] = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        def wilder(arr, p):
            out = np.zeros(n)
            out[p] = arr[1:p + 1].sum()
            for i in range(p + 1, n):
                out[i] = out[i - 1] - out[i - 1] / p + arr[i]
            return out

        atr14 = wilder(tr, period)
        pdm14 = wilder(plus_dm, period)
        mdm14 = wilder(minus_dm, period)
        eps = 1e-10
        dx = 100 * np.abs(pdm14 / (atr14 + eps) - mdm14 / (atr14 + eps)) / \
             (pdm14 / (atr14 + eps) + mdm14 / (atr14 + eps) + eps)
        adx = np.zeros(n)
        adx[2 * period] = dx[period:2 * period + 1].mean()
        for i in range(2 * period + 1, n):
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period
        return float(adx[-1])
    except Exception:
        return 0.0
