#!/usr/bin/env python3
"""
synap/ticker_poller.py — Poller for Top 20 Volatility Ticker

- Every 2 hours: Scans Hyperliquid for the Top 20 most volatile coins.
- Every 40 seconds: Fetches the latest markPx and prevDayPx for these 20 coins, 
  calculates the 24h percentage change, and saves it to db.market_data.
"""

import time
import logging
import traceback
import json
from datetime import datetime, timezone

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import get_sync_db
from synap.market_data import RESTInfo
from hyperliquid.utils import constants

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Config
TOP_N_COINS = 20
POLL_INTERVAL_SECONDS = 40
COIN_REFRESH_INTERVAL_SECONDS = 7200  # 2 hours

def get_top_volatile_coins_metadata(limit=20):
    """
    Returns a list of dicts: {"coin": "BTC", "change_pct": 0.05, "price": 60000.0}
    for the most volatile coins in the last 24h.
    """
    info = RESTInfo(constants.MAINNET_API_URL, skip_ws=True)
    meta_and_ctxs = info.meta_and_asset_ctxs()
    
    if not meta_and_ctxs or len(meta_and_ctxs) < 2:
        return []
        
    universe = meta_and_ctxs[0].get("universe") or []
    ctxs = meta_and_ctxs[1]
    
    coin_data = []
    
    for asset, ctx in zip(universe, ctxs):
        coin = asset["name"]
        prev_price = float(ctx.get("prevDayPx", ctx.get("prevDayPrice", 0)))
        curr_price = float(ctx.get("markPx", ctx.get("markPrice", 0)))
        
        if prev_price > 0:
            change_pct = (curr_price - prev_price) / prev_price
            abs_change = abs(change_pct)
            coin_data.append({
                "coin": coin,
                "change_pct": change_pct,
                "abs_change": abs_change,
                "price": curr_price
            })
            
    # Sort by absolute change descending
    coin_data.sort(key=lambda x: x["abs_change"], reverse=True)
    
    # Return top N, stripping out the 'abs_change' helper key
    top_coins = []
    for cd in coin_data[:limit]:
        top_coins.append({
            "coin": cd["coin"],
            "change_pct": cd["change_pct"],
            "price": cd["price"]
        })
        
    return top_coins

def get_specific_coins_metadata(coins_list):
    """
    Given a list of coin tickers, fetch their current price and % change.
    """
    info = RESTInfo(constants.MAINNET_API_URL, skip_ws=True)
    meta_and_ctxs = info.meta_and_asset_ctxs()
    
    if not meta_and_ctxs or len(meta_and_ctxs) < 2:
        return []
        
    universe = meta_and_ctxs[0].get("universe") or []
    ctxs = meta_and_ctxs[1]
    
    coin_data = []
    
    for asset, ctx in zip(universe, ctxs):
        coin = asset["name"]
        if coin in coins_list:
            prev_price = float(ctx.get("prevDayPx", ctx.get("prevDayPrice", 0)))
            curr_price = float(ctx.get("markPx", ctx.get("markPrice", 0)))
            if prev_price > 0:
                change_pct = (curr_price - prev_price) / prev_price
                coin_data.append({
                    "coin": coin,
                    "change_pct": change_pct,
                    "price": curr_price
                })
                
    # Keep original order of volatility from the input list
    coin_data.sort(key=lambda x: coins_list.index(x["coin"]) if x["coin"] in coins_list else 999)
    return coin_data

def run_poller():
    logger.info("🚀 Starting Volatility Ticker Poller...")
    last_top_coins_refresh = 0
    cached_top_coins = []
    
    db = get_sync_db()
    
    while True:
        try:
            current_time = time.time()
            
            # 1. Update the list of Top 20 coins every 2 hours
            if current_time - last_top_coins_refresh >= COIN_REFRESH_INTERVAL_SECONDS or not cached_top_coins:
                logger.info(f"🔄 Recalculating Top {TOP_N_COINS} Volatility Leaders...")
                full_metadata = get_top_volatile_coins_metadata(limit=TOP_N_COINS)
                cached_top_coins = [c["coin"] for c in full_metadata]
                live_data = full_metadata
                last_top_coins_refresh = current_time
            else:
                # 2. Update prices for the cached Top 20 coins every 40s
                logger.info(f"⚡ Polling latest prices for {len(cached_top_coins)} volatile coins...")
                live_data = get_specific_coins_metadata(cached_top_coins)
                
            # 3. Save to MongoDB
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": live_data
            }
            
            db.market_data.update_one(
                {"key": "volatility_ticker_top_20"},
                {"$set": {"value_json": json.dumps(payload)}},
                upsert=True
            )
            
            logger.info("✅ Saved updated ticker data to database.")
            
        except Exception as e:
            logger.error(f"❌ Poller Error: {e}")
            logger.error(traceback.format_exc())
            
        # Sleep for 40 seconds
        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_poller()
