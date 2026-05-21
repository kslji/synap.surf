import asyncio
import logging
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from backend.db import get_db, set_market_data, log_trade
from algo_brain.config import HL_WALLET
from algo_brain import market_data
from algo_brain import news_sentiment
from algo_brain import nansen_client

logger = logging.getLogger("backend.services")

async def volatility_service():
    """Fetches top volatility coins every 30 minutes."""
    while True:
        try:
            logger.info("Running Volatility Service (Top Perps)...")
            top_data = await asyncio.to_thread(market_data.get_top_3_perps_with_details)
            if top_data and top_data.get("ctxs"):
                await asyncio.to_thread(set_market_data, 'top_perps', {
                    "data": top_data,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
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
                with get_db() as db:
                    row = db.execute("SELECT value_json FROM market_data WHERE key = 'top_perps'").fetchone()
                    import json
                    if row:
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
            
            set_market_data('market_intelligence_global', intel)
            logger.info("Updated raw market intelligence.")
            
        except Exception as e:
            logger.error(f"Error in market_intel_service: {e}")
            
        await asyncio.sleep(1800) # 30 minutes

async def trade_history_sync_service():
    """Fetches user_fills from Hyperliquid to capture manual trades, runs every 5 minutes."""
    while True:
        try:
            if HL_WALLET:
                # Need to run blocking Info call in an executor
                from hyperliquid.info import Info
                from hyperliquid.utils import constants
                
                info = Info(constants.MAINNET_API_URL, skip_ws=True)
                fills = await asyncio.to_thread(info.user_fills, HL_WALLET)
                
                # Deduplicate and sync to trade_logs
                if fills:
                    with get_db() as db:
                        # Get latest trade timestamp from DB to avoid inserting old fills
                        last_db_trade = db.execute("SELECT timestamp FROM trade_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (HL_WALLET,)).fetchone()
                        # We use a simple strategy: insert fills that are newer than 24h, and use unique constraints or check existing.
                        # Since trade_logs doesn't have a strict unique ID from HL right now, we will do a basic check by timestamp and coin.
                        
                        for fill in fills:
                            fill_time = fill.get("time", 0)
                            dt = datetime.fromtimestamp(fill_time / 1000, tz=timezone.utc)
                            
                            # Simple deduplication (assuming we don't insert same coin side at exact same millisecond)
                            existing = db.execute("SELECT id FROM trade_logs WHERE user_id = ? AND coin = ? AND side = ? AND timestamp = ?", 
                                                  (HL_WALLET, fill["coin"], fill["dir"], dt)).fetchone()
                            
                            if not existing:
                                # Determine if it's manual. A true link would match exactly with AI trades. 
                                # For MVP, we insert it as a MANUAL_FILL if it's missing.
                                sz = float(fill.get("sz", 0))
                                px = float(fill.get("px", 0))
                                pnl = float(fill.get("closedPnl", 0))
                                db.execute('''
                                    INSERT INTO trade_logs (user_id, event, coin, side, entry_price, exit_price, pnl_usd, position_size_usd, action, details, timestamp)
                                    VALUES (?, 'FILL', ?, ?, ?, ?, ?, ?, 'MANUAL_OR_EXTERNAL_TRADE', 'Direct fill from exchange', ?)
                                ''', (HL_WALLET, fill["coin"], fill["dir"], px, px if pnl != 0 else None, pnl if pnl != 0 else None, sz * px, dt))
        except Exception as e:
            logger.error(f"Error in trade_history_sync_service: {e}")
            
        await asyncio.sleep(300) # 5 minutes
