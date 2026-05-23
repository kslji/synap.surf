import asyncio
import logging
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from backend.database import get_async_db
from synap import market_data

logger = logging.getLogger("backend.services.volatility")

async def run_service():
    """Fetches top volatility coins every 30 minutes."""
    db = get_async_db()
    while True:
        try:
            logger.info("Running Volatility Service (Top Perps)...")
            top_data = await asyncio.to_thread(market_data.get_top_3_perps_with_details)
            if top_data and top_data.get("ctxs"):
                doc = {
                    "key": "top_perps",
                    "value_json": {
                        "data": top_data,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    },
                    "updated_at": datetime.now(timezone.utc)
                }
                # Using PyMongo style with Motor
                import json
                doc["value_json"] = json.dumps(doc["value_json"], default=str)
                await db.market_data.update_one(
                    {"key": "top_perps"},
                    {"$set": doc},
                    upsert=True
                )
                logger.info("Updated top_perps cache")
        except Exception as e:
            logger.error(f"Error in volatility_service: {e}")
        
        await asyncio.sleep(1800) # 30 minutes
