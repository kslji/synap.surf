import asyncio
import logging
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from backend.database import get_async_db
# set_market_data and log_trade should be updated too

from synap import market_data
from synap import news_sentiment
from synap import nansen_client

logger = logging.getLogger("backend.services")

async def volatility_service():
    """Fetches top volatility coins every 30 minutes."""
    while True:
        try:
            logger.info("Running Volatility Service (Top Perps)...")
            top_data = await asyncio.to_thread(market_data.get_top_3_perps_with_details)
            if top_data and top_data.get("ctxs"):
                db = get_async_db()
                import json
                await db.market_data.update_one({'key': 'top_perps'}, {'$set': {'value_json': json.dumps({
                    "data": top_data,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })}}, upsert=True)
                logger.info("Updated top_perps cache")
        except Exception as e:
            logger.error(f"Error in volatility_service: {e}")
        
        await asyncio.sleep(1800) # 30 minutes

async def market_intel_service():
    """Fetches combined market intelligence (news + on-chain) every 30 minutes."""
    while True:
        try:
            # We wait a bit on startup to let volatility service run first
            await asyncio.sleep(10)
            logger.info("Running Market Intelligence Service...")
            
            # 1. Get top volatile coins from DB to focus our search
            target_coins = ["BTC", "ETH", "SOL"]
            try:
                db = get_async_db()
                row = await db.market_data.find_one({"key": "top_perps"})
                import json
                if row and "value_json" in row:
                    vol_data = json.loads(row["value_json"])
                    ctxs = vol_data.get("data", {}).get("ctxs", [])
                    if ctxs:
                        target_coins = [c["name"] for c in ctxs[:5]]
            except Exception:
                pass
            
            # 2. Fetch News & Sentiment
            sentiment = await asyncio.to_thread(news_sentiment.build_sentiment_data, target_coins)
            
            # 3. Fetch Nansen data (if configured)
            nansen_data = await asyncio.to_thread(nansen_client.build_nansen_intelligence, target_coins)
            
            # We just merge the data into a generic payload
            intel = {
                "sentiment": sentiment,
                "on_chain_flows": nansen_data.get("smart_money_flows", {}),
                "screener_highlights": nansen_data.get("perp_screener", {}),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            db = get_async_db()
            await db.market_data.update_one({'key': 'market_intelligence'}, {'$set': {'value_json': json.dumps(intel)}}, upsert=True)
            logger.info("Updated raw market intelligence.")
            
        except Exception as e:
            logger.error(f"Error in market_intel_service: {e}")
            
        await asyncio.sleep(1800) # 30 minutes

async def trade_history_sync_service():
    """Fetches user_fills from Hyperliquid into trade_logs; runs every 5 minutes."""
    from backend.trade_sync import sync_all_registered_wallets

    from hyperliquid.info import Info
    from hyperliquid.utils import constants

    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    db = get_async_db()

    while True:
        try:
            n = await sync_all_registered_wallets(db, info=info)
            if n:
                logger.info("trade_history_sync_service: inserted %s fills", n)
        except Exception as e:
            logger.error("Error in trade_history_sync_service: %s", e)

        await asyncio.sleep(300)


PROTECTED_EVENTS = {"TRADE_OPEN", "TRADE_CLOSE"}
FILL_KEEP_LIMIT = 50

async def trade_cleanup_service():
    """
    Keeps trade_logs manageable per user:
    - TRADE_OPEN / TRADE_CLOSE (BOT events) are never deleted — they are the source
      of truth for AI signals, positions, and P&L history.
    - FILL events (exchange sync) are capped at FILL_KEEP_LIMIT most recent.
    Runs every 5 minutes.
    """
    while True:
        try:
            db = get_async_db()
            users = await db.trade_logs.distinct("user_id")
            if None not in users:
                users.append(None)

            for user in users:
                if user:
                    base_query = {"user_id": user}
                else:
                    base_query = {"user_id": {"$in": [None, ""]}}

                # Only clean up FILL/FILLED events — never touch BOT trade records
                fill_query = {**base_query, "event": {"$nin": list(PROTECTED_EVENTS)}}
                fills = await db.trade_logs.find(fill_query).sort("timestamp", -1).to_list(length=None)

                if len(fills) > FILL_KEEP_LIMIT:
                    old_ids = [t["_id"] for t in fills[FILL_KEEP_LIMIT:]]
                    res = await db.trade_logs.delete_many({"_id": {"$in": old_ids}})
                    if res.deleted_count:
                        logger.info(f"🗑️ trade_cleanup: removed {res.deleted_count} old FILLs for {str(user or 'SYSTEM')[:10]}")

        except Exception as e:
            logger.error(f"Error in trade_cleanup_service: {e}")

        await asyncio.sleep(300)

