#!/usr/bin/env python3
"""
brain/market_data.py — Multi-coin Hyperliquid data fetcher + technical analysis.
Fetches OHLC candles, funding rates, and computes quick technicals for any
perp listed on Hyperliquid.
"""

import time
import logging
from typing import Optional

import pandas as pd
from hyperliquid.info import Info
from hyperliquid.utils import constants

from algo_brain.config import (
    CANDLE_INTERVAL,
    CANDLE_LOOKBACK,
)
from algo_brain import strategies

logger = logging.getLogger(__name__)

# ─── Singleton Hyperliquid client ────────────────────────────────────────────
_info: Optional[Info] = None


def _get_info() -> Info:
    global _info
    if _info is None:
        _info = Info(constants.MAINNET_API_URL, skip_ws=True)
    return _info


# ═══════════════════════════════════════════════════════════════════════════════
# DYNAMIC COIN SELECTION (Volatility Based)
# ═══════════════════════════════════════════════════════════════════════════════


def get_all_perp_coins() -> list[dict]:
    """
    Get all available perp coins on Hyperliquid from meta endpoint.
    """
    try:
        info = _get_info()
        meta = info.meta()
        coins = []
        for asset in meta.get("universe") or []:
            name = asset["name"]
            # Exclude index-like assets if any, though HL usually perps
            coins.append({"name": name, "szDecimals": asset["szDecimals"]})
        return coins
    except Exception as e:
        logger.error(f"Failed to fetch Hyperliquid meta: {e}")
        return []


def get_coin_names() -> list[str]:
    """Return just the coin name strings (e.g., ['BTC', 'ETH', 'SOL', ...])."""
    return [c["name"] for c in get_all_perp_coins()]


def get_top_volatility_coins(limit: int = 10) -> list[str]:
    """
    Scan the entire Hyperliquid universe and return the top 'limit' coins
    with the highest absolute price fluctuation over the last 24h.
    This captures both big winners (longs) and big losers (shorts).
    """
    try:
        info = _get_info()
        meta_and_ctxs = info.meta_and_asset_ctxs()
        if not meta_and_ctxs or len(meta_and_ctxs) < 2:
            return ["BTC", "ETH", "SOL"]

        universe = meta_and_ctxs[0].get("universe") or []
        ctxs = meta_and_ctxs[1]

        volatility_list = []

        for asset, ctx in zip(universe, ctxs):
            coin = asset["name"]
            # Hyperliquid uses 'prevDayPx' and 'markPx' for 24h stats
            prev_price = float(ctx.get("prevDayPx", ctx.get("prevDayPrice", 0)))
            curr_price = float(ctx.get("markPx", ctx.get("markPrice", 0)))

            if prev_price > 0:
                # Calculate absolute % change
                change_pct = abs((curr_price - prev_price) / prev_price)
                volatility_list.append((coin, change_pct))

        # Sort by change_pct descending
        volatility_list.sort(key=lambda x: x[1], reverse=True)

        # Extract top N symbols
        top_coins = [item[0] for item in volatility_list[:limit]]

        # Majors (BTC, ETH, SOL) removed per user request to focus PURELY on volatility.
        # They will still be traded IF they are among the most volatile.

        logger.info(f"🔥 Volatility Leaders: {', '.join(top_coins)}")
        return top_coins
    except Exception as e:
        logger.error(f"Failed to scan volatility: {e}")
        return ["BTC", "ETH", "SOL"]


# ═══════════════════════════════════════════════════════════════════════════════
# OHLC CANDLES
# ═══════════════════════════════════════════════════════════════════════════════


def fetch_candles(
    coin: str,
    interval: str = CANDLE_INTERVAL,
    n: int = CANDLE_LOOKBACK,
) -> Optional[pd.DataFrame]:
    """
    Fetch recent OHLC candles from Hyperliquid for any coin.
    Returns DataFrame with columns: open_time_utc, open, high, low, close, volume
    """
    try:
        info = _get_info()
        now_ms = int(time.time() * 1000)

        # Calculate ms per interval
        interval_map = {
            "1m": 60_000,
            "5m": 300_000,
            "15m": 900_000,
            "30m": 1_800_000,
            "1h": 3_600_000,
            "4h": 14_400_000,
            "1d": 86_400_000,
        }
        ms_per_candle = interval_map.get(interval, 1_800_000)
        start_ms = now_ms - (n * ms_per_candle)

        candles = info.candles_snapshot(coin, interval, start_ms, now_ms)

        if not candles:
            logger.warning(f"No candles returned for {coin}")
            return None

        df = pd.DataFrame(candles)
        df.rename(
            columns={
                "t": "open_time_ms",
                "T": "close_time_ms",
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
                "v": "volume",
            },
            inplace=True,
        )

        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = df[col].astype(float)

        if "open_time_ms" in df.columns:
            df["open_time_ms"] = df["open_time_ms"].astype("int64")
            df["open_time_utc"] = pd.to_datetime(
                df["open_time_ms"], unit="ms", utc=True
            )

        df = df.sort_values("open_time_ms").tail(n).reset_index(drop=True)
        return df

    except Exception as e:
        logger.error(f"Failed to fetch candles for {coin}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# FUNDING RATES
# ═══════════════════════════════════════════════════════════════════════════════


def get_all_funding_rates() -> dict[str, float]:
    """
    Get current funding rates for all perps.
    Positive = longs pay shorts (bearish signal when extreme).
    Negative = shorts pay longs (bullish signal when extreme).
    """
    try:
        info = _get_info()
        # The funding data comes from the meta_and_asset_ctxs endpoint
        meta_and_ctxs = info.meta_and_asset_ctxs()

        funding = {}
        if len(meta_and_ctxs) >= 2:
            universe = meta_and_ctxs[0].get("universe") or []
            ctxs = meta_and_ctxs[1]
            for asset, ctx in zip(universe, ctxs):
                coin = asset["name"]
                funding[coin] = float(ctx.get("funding", 0))

        return funding

    except Exception as e:
        logger.error(f"Failed to fetch funding rates: {e}")
        return {}


def get_mid_prices() -> dict[str, float]:
    """Get current mid prices for all coins."""
    try:
        info = _get_info()
        mids = info.all_mids()
        return {k: float(v) for k, v in mids.items()}
    except Exception as e:
        logger.error(f"Failed to fetch mid prices: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# QUICK TECHNICAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════


def compute_technicals(df: pd.DataFrame) -> dict:
    """
    Compute technical indicators and regimes using the strategies library.
    Returns a dict of indicator values for Claude to analyze.
    """
    return strategies.calculate_all(df)


def get_mtf_technicals(coin: str) -> dict:
    """
    Fetch and compute technicals for both FAST (1m) and SLOW (30m) timeframes.
    This gives Claude the ability to see 1-minute scalps and 2-day trends.
    """
    from algo_brain.config import FAST_INTERVAL, SLOW_INTERVAL, CANDLE_LOOKBACK

    results = {}

    # 1. Fast timeframe (micro-moves)
    df_fast = fetch_candles(coin, interval=FAST_INTERVAL, n=CANDLE_LOOKBACK)
    if df_fast is not None:
        results["fast"] = compute_technicals(df_fast)
        results["fast"]["interval"] = FAST_INTERVAL

    # 2. Slow timeframe (macro-trend)
    df_slow = fetch_candles(coin, interval=SLOW_INTERVAL, n=CANDLE_LOOKBACK)
    if df_slow is not None:
        results["slow"] = compute_technicals(df_slow)
        results["slow"]["interval"] = SLOW_INTERVAL

    return results


def get_top_3_perps_with_details() -> dict:
    """
    Returns top 3 most volatile perps with metadata for the dashboard.
    Called by the dashboard server to bypass browser CORS.
    """
    try:
        info = _get_info()
        meta_and_ctxs = info.meta_and_asset_ctxs()
        if not meta_and_ctxs or len(meta_and_ctxs) < 2:
            return {"meta": {"universe": []}, "ctxs": []}

        universe = meta_and_ctxs[0].get("universe") or []
        ctxs = meta_and_ctxs[1]

        res = []
        for asset, ctx in zip(universe, ctxs):
            res.append(
                {
                    "name": asset["name"],
                    "markPx": ctx.get("markPx"),
                    "prevDayPx": ctx.get("prevDayPx"),
                    "dayNtlVlm": ctx.get("dayNtlVlm"),
                }
            )
        return {"meta": {"universe": universe}, "ctxs": res}
    except Exception as e:
        logger.error(f"Error fetching top perps: {e}")
        return {"meta": {"universe": []}, "ctxs": []}
