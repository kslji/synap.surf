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
    """Fetches user_fills from Hyperliquid to capture manual trades, runs every 5 minutes."""
    while True:
        try:
            from hyperliquid.info import Info
            from hyperliquid.utils import constants
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            
            db = get_async_db()
            rows = await db.users.find({}).to_list(length=None)
            users = [r.get("wallet_address") for r in rows if r.get("wallet_address")]
                
            for wallet in users:
                if not wallet or not wallet.startswith('0x') or len(wallet) != 42:
                    continue
                try:
                    fills = await asyncio.to_thread(info.user_fills, wallet)
                    
                    if fills:
                        for fill in fills:
                            fill_time = fill.get("time", 0)
                            dt = datetime.fromtimestamp(fill_time / 1000, tz=timezone.utc)
                            
                            # Check if this exact fill is already logged in the DB
                            existing_exact = await db.trade_logs.find_one({
                                "user_id": wallet,
                                "coin": fill["coin"],
                                "event": "FILL",
                                "side": fill["dir"],
                                "timestamp": dt
                            })
                            
                            if not existing_exact:
                                fill_dir = fill.get("dir", "")
                                is_close = "Close" in fill_dir
                                sz = float(fill.get("sz", 0))
                                px = float(fill.get("px", 0))
                                pnl = float(fill.get("closedPnl", 0))
                                
                                # Search for a matching local trade log in the last 90 seconds
                                # (e.g. EXECUTED worker logs or TRADE_OPEN/TRADE_CLOSE manual logs)
                                dt_start = dt - timedelta(seconds=90)
                                dt_end = dt + timedelta(seconds=90)
                                local_match = None
                                
                                async for row in db.trade_logs.find({
                                    "user_id": wallet,
                                    "coin": fill["coin"],
                                    "event": {"$ne": "FILL"}
                                }):
                                    row_ts = row.get("timestamp")
                                    if not row_ts:
                                        continue
                                    if isinstance(row_ts, str):
                                        try:
                                            row_dt = datetime.fromisoformat(row_ts.replace("Z", "+00:00"))
                                        except Exception:
                                            continue
                                    else:
                                        row_dt = row_ts
                                        
                                    if row_dt.tzinfo is None:
                                        row_dt = row_dt.replace(tzinfo=timezone.utc)
                                        
                                    if dt_start <= row_dt <= dt_end:
                                        row_side = row.get("side", "")
                                        row_event = row.get("event")
                                        
                                        is_match = False
                                        if is_close:
                                            if row_event == "TRADE_CLOSE" or "Close" in row_side:
                                                is_match = True
                                        else:
                                            if row_event == "TRADE_OPEN" or row.get("status") == "EXECUTED" or "Open" in row_side:
                                                is_match = True
                                                
                                        if is_match:
                                            local_match = row
                                            break
                                            
                                if local_match:
                                    # Update and merge the exchange details into the existing local log to prevent duplication
                                    action_type = "AI_BOT_TRADE"
                                    details_str = "Synchronized AI execution"
                                    
                                    if local_match.get("reasoning") == "Manual UI Close" or local_match.get("event") == "TRADE_CLOSE":
                                        action_type = "MANUAL_UI_CLOSE"
                                        details_str = "Synchronized manual close"
                                    elif local_match.get("reasoning") == "Manual UI Trade" or local_match.get("event") == "TRADE_OPEN":
                                        action_type = "MANUAL_UI_TRADE"
                                        details_str = "Synchronized manual open"
                                        
                                    await db.trade_logs.update_one(
                                        {"_id": local_match["_id"]},
                                        {"$set": {
                                            "event": "FILL",
                                            "side": fill_dir,
                                            "entry_price": px if not is_close else local_match.get("entry_price", px),
                                            "exit_price": px if is_close else None,
                                            "pnl_usd": pnl if is_close else None,
                                            "position_size_usd": sz * px,
                                            "action": action_type,
                                            "details": details_str,
                                            "timestamp": dt,
                                            "status": "FILLED"
                                        }}
                                    )
                                    logger.info(f"🔄 Merged and synced HL fill for {fill['coin']} into local matched log")
                                else:
                                    # Insert as a new manual/external fill since no local match was found
                                    await db.trade_logs.insert_one({
                                        "user_id": wallet,
                                        "event": "FILL",
                                        "coin": fill["coin"],
                                        "side": fill["dir"],
                                        "entry_price": px,
                                        "exit_price": px if pnl != 0 else None,
                                        "pnl_usd": pnl if pnl != 0 else None,
                                        "position_size_usd": sz * px,
                                        "action": "MANUAL_OR_EXTERNAL_TRADE",
                                        "details": "Direct fill from exchange",
                                        "timestamp": dt
                                    })
                                    logger.info(f"📥 Logged new external fill for {fill['coin']} ({fill_dir})")
                except Exception as ex:
                    logger.error(f"Error fetching fills for {wallet}: {ex}")
        except Exception as e:
            logger.error(f"Error in trade_history_sync_service: {e}")
            
        await asyncio.sleep(300) # 5 minutes


async def trade_cleanup_service():
    """Keeps only the 20 most recent trade logs for each user and system-wide, runs every 5 minutes."""
    while True:
        try:
            db = get_async_db()
            
            # Get distinct user_ids
            users = await db.trade_logs.distinct("user_id")
            
            # Ensure we also check for None or empty string user_ids (for global/system logs)
            if None not in users:
                users.append(None)
                
            for user in users:
                if user:
                    query = {"user_id": user}
                else:
                    query = {"user_id": {"$in": [None, ""]}}
                    
                # Find all trade logs for this user/system, sorted by timestamp descending
                trades = await db.trade_logs.find(query).sort("timestamp", -1).to_list(length=None)
                
                if len(trades) > 20:
                    old_ids = [t["_id"] for t in trades[20:]]
                    res = await db.trade_logs.delete_many({"_id": {"$in": old_ids}})
                    logger.info(f"🗑️ trade_cleanup_service: Cleaned up {res.deleted_count} old trade logs for user/system {user or 'SYSTEM'}")
                    
        except Exception as e:
            logger.error(f"Error in trade_cleanup_service: {e}")
            
        await asyncio.sleep(300) # 5 minutes

