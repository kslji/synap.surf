#!/usr/bin/env python3
"""
brain/nansen_client.py — Nansen API client with credit-aware rate limiting.
Fetches smart money data, perp screener, and token flows.

Credit budget: 1000/month → system uses ≈600, leaving 400 buffer.
All responses are cached (TTL = 4 hours) to minimize API calls.
"""

import json
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

import requests

from algo_brain.config import (
    NANSEN_API_KEY,
    NANSEN_BASE_URL,
    NANSEN_MONTHLY_BUDGET,
    NANSEN_BUDGET_WARNING_PCT,
    NANSEN_CACHE_TTL_SECONDS,
)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from backend.db import get_db

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CREDIT TRACKER
# ═══════════════════════════════════════════════════════════════════════════════


class NansenCreditTracker:
    """Tracks Nansen API credit usage to stay within monthly budget."""

    def __init__(self):
        self.credits_used = 0
        self.month_start = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0
        )
        self._load()

    def _load(self):
        try:
            with get_db() as db:
                row = db.execute("SELECT value_json FROM market_data WHERE key = 'nansen_credits'").fetchone()
                if row:
                    data = json.loads(row["value_json"])
                    saved_month = datetime.fromisoformat(data["month_start"])
                    # Reset if new month
                    if saved_month.month != datetime.now(timezone.utc).month:
                        self.credits_used = 0
                        self._save()
                    else:
                        self.credits_used = data.get("credits_used", 0)
                        self.month_start = saved_month
        except Exception:
            pass

    def _save(self):
        try:
            data = {
                "credits_used": self.credits_used,
                "month_start": self.month_start.isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            with get_db() as db:
                db.execute('''
                    INSERT INTO market_data (key, value_json) VALUES ('nansen_credits', ?)
                    ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=CURRENT_TIMESTAMP
                ''', (json.dumps(data, default=str),))
        except Exception as e:
            logger.warning(f"Failed to save credit tracker: {e}")

    def use_credit(self, count: int = 1):
        self.credits_used += count
        remaining = NANSEN_MONTHLY_BUDGET - self.credits_used
        pct_used = self.credits_used / NANSEN_MONTHLY_BUDGET

        if pct_used >= NANSEN_BUDGET_WARNING_PCT:
            logger.warning(
                f"⚠️  Nansen credits: {self.credits_used}/{NANSEN_MONTHLY_BUDGET} used "
                f"({pct_used * 100:.0f}%) — {remaining} remaining"
            )
        else:
            logger.info(
                f"💳 Nansen credit used. Total: {self.credits_used}/{NANSEN_MONTHLY_BUDGET} "
                f"({remaining} remaining)"
            )
        self._save()

    def can_call(self) -> bool:
        if self.credits_used >= NANSEN_MONTHLY_BUDGET:
            logger.error("🚫 Nansen monthly budget exhausted! Skipping API call.")
            return False
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE CACHE
# ═══════════════════════════════════════════════════════════════════════════════


class _Cache:
    """Simple in-memory cache with TTL."""

    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            ts, val = self._store[key]
            if time.time() - ts < NANSEN_CACHE_TTL_SECONDS:
                logger.info(f"  📦 Cache hit: {key}")
                return val
            else:
                del self._store[key]
        return None

    def set(self, key: str, value: Any):
        self._store[key] = (time.time(), value)


_cache = _Cache()
_tracker = NansenCreditTracker()


# ═══════════════════════════════════════════════════════════════════════════════
# NANSEN API CLIENT
# ═══════════════════════════════════════════════════════════════════════════════


def _headers() -> dict:
    return {
        "apikey": NANSEN_API_KEY,
        "Content-Type": "application/json",
    }


def _nansen_post(endpoint: str, body: dict, cache_key: str) -> Optional[dict]:
    """Make a POST request to Nansen with caching and credit tracking."""
    if not NANSEN_API_KEY:
        logger.warning("NANSEN_API_KEY not set — skipping Nansen call")
        return None

    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    if not _tracker.can_call():
        return None

    url = f"{NANSEN_BASE_URL}/{endpoint}"
    resp = None
    try:
        logger.info(f"🔍 Nansen API: POST {endpoint}")
        resp = requests.post(url, headers=_headers(), json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        _tracker.use_credit()
        _cache.set(cache_key, data)
        return data
    except requests.exceptions.HTTPError as e:
        if resp is not None:
            logger.error(f"Nansen API error ({resp.status_code}): {e}")
            # Try to log the response body for debugging
            try:
                logger.error(f"Response: {resp.text[:500]}")
            except Exception:
                pass
        else:
            logger.error(f"Nansen HTTP error (no response): {e}")
        return None
    except Exception as e:
        logger.error(f"Nansen request failed: {e}")
        return None


def _nansen_get(endpoint: str, params: dict, cache_key: str) -> Optional[dict]:
    """Make a GET request to Nansen with caching and credit tracking."""
    if not NANSEN_API_KEY:
        logger.warning("NANSEN_API_KEY not set — skipping Nansen call")
        return None

    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    if not _tracker.can_call():
        return None

    url = f"{NANSEN_BASE_URL}/{endpoint}"
    resp = None
    try:
        logger.info(f"🔍 Nansen API: GET {endpoint}")
        resp = requests.get(url, headers=_headers(), params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        _tracker.use_credit()
        _cache.set(cache_key, data)
        return data
    except requests.exceptions.HTTPError as e:
        if resp is not None:
            logger.error(f"Nansen API error ({resp.status_code}): {e}")
            try:
                logger.error(f"Response: {resp.text[:500]}")
            except Exception:
                pass
        else:
            logger.error(f"Nansen HTTP error (no response): {e}")
        return None
    except Exception as e:
        logger.error(f"Nansen request failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def get_perp_screener() -> Optional[dict]:
    """
    Fetch top perps on Hyperliquid by smart money activity.
    Shows OI, volume, funding, and smart money positioning.
    Uses a 2-day rolling window — Nansen has a data lag so today-only queries return empty.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    return _nansen_post(
        "perp-screener",
        {
            "date": {"from": yesterday, "to": today},
            "pagination": {"page": 1, "per_page": 50},
        },
        cache_key=f"perp_screener_{today}",
    )


def get_smart_money_netflows(coin: str) -> Optional[dict]:
    """
    Get smart money net inflows/outflows for a specific coin.
    Note: Nansen v1 netflow endpoint returns a list; we filter locally.
    """
    data = _nansen_post(
        "smart-money/netflow",
        {
            "chains": ["ethereum", "solana", "arbitrum", "base", "polygon"],
            "pagination": {"page": 1, "per_page": 100},
        },
        cache_key="sm_netflow_all_24h",
    )

    if not data or "data" not in data:
        return None

    # Filter for the specific coin symbol
    coin_upper = coin.upper()
    for item in data["data"]:
        if item.get("token_symbol") == coin_upper:
            return item

    return None


def get_token_screener(chains: Optional[list[str]] = None) -> Optional[dict]:
    """
    Discover trending tokens across chains.
    Useful for narrative detection.
    """
    body = {
        "chains": chains or ["ethereum", "solana", "base"],
        "timeframe": "24h",
        "pagination": {"page": 1, "per_page": 20},
    }
    return _nansen_post(
        "token-screener",
        body,
        cache_key="token_screener_24h",
    )


def get_smart_money_perp_trades(coin: Optional[str] = None) -> Optional[dict]:
    """
    Get smart money perpetual trading activity.
    Focuses on Hyperliquid positions.
    """
    body = {"platform": "hyperliquid", "timeframe": "24h"}
    if coin:
        body["symbol"] = coin
    return _nansen_post(
        "smart-money/perp-trades",
        body,
        cache_key=f"sm_perp_trades_{coin or 'all'}_24h",
    )


def build_nansen_intelligence(coins: list[str]) -> dict:
    """
    Build a comprehensive Nansen intelligence report for the given coins.
    This is the main entry point called by the brain each cycle.

    Returns structured data ready for Claude:
    {
        "perp_screener": {...},
        "smart_money_flows": {"SOL": {...}, "ETH": {...}},
        "token_trends": {...},
        "credits_used": 5,
        "credits_remaining": 995,
    }
    """
    result = {
        "perp_screener": None,
        "smart_money_flows": {},
        "token_trends": None,
        "credits_used": _tracker.credits_used,
        "credits_remaining": NANSEN_MONTHLY_BUDGET - _tracker.credits_used,
    }

    # 1. Perp screener (1 credit)
    result["perp_screener"] = get_perp_screener()

    # 2. Smart money netflows for each coin (1 credit each)
    for coin in coins[:6]:  # Cap at 6 coins to save credits
        flow = get_smart_money_netflows(coin)
        if flow:
            result["smart_money_flows"][coin] = flow

    # 3. Token screener for narrative trends (1 credit)
    result["token_trends"] = get_token_screener()

    # Update credit counts
    result["credits_used"] = _tracker.credits_used
    result["credits_remaining"] = NANSEN_MONTHLY_BUDGET - _tracker.credits_used

    logger.info(
        f"📊 Nansen intelligence built. Credits: {_tracker.credits_used}/{NANSEN_MONTHLY_BUDGET}"
    )

    return result
