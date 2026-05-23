import asyncio
import logging
from datetime import datetime, timezone
import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from backend.database import get_async_db
from synap import news_sentiment
from synap import nansen_client

logger = logging.getLogger("backend.services.market_intel")

async def run_service():
    """Fetches combined market intelligence (news + on-chain) every 30 minutes."""
    db = get_async_db()
    while True:
        try:
            # We wait a bit on startup to let volatility service run first
            await asyncio.sleep(10)
            logger.info("Running Market Intelligence Service...")
            
            # 1. Get top volatile coins from DB to focus our search
            target_coins = ["BTC", "ETH", "SOL"]
            try:
                row = await db.market_data.find_one({"key": "top_perps"})
                if row and "value_json" in row:
                    vol_data = json.loads(row["value_json"]) if isinstance(row["value_json"], str) else row["value_json"]
                    ctxs = vol_data.get("data", {}).get("ctxs", [])
                    if ctxs:
                        target_coins = [c["name"] for c in ctxs[:5]]
            except Exception as e:
                logger.error(f"Failed to read top_perps for intel: {e}")
            
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
            
            doc = {
                "key": "market_intelligence",
                "value_json": json.dumps(intel, default=str),
                "updated_at": datetime.now(timezone.utc)
            }
            await db.market_data.update_one(
                {"key": "market_intelligence"},
                {"$set": doc},
                upsert=True
            )
            logger.info("Updated raw market intelligence.")
            
        except Exception as e:
            logger.error(f"Error in market_intel_service: {e}")
            
        await asyncio.sleep(1800) # 30 minutes
