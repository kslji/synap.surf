import os
import sys
import json
import time
import logging
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from synap.config import CORE_WATCHLIST
from synap import market_data
from synap import news_sentiment
from backend.database import get_sync_db as get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s | Maintainer | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# How often to run the data collection (in seconds)
MAINTAINER_INTERVAL = 3600 # 1 Hour

last_vol_update_time = 0
cached_vol_leaders = []

def run_maintainer_cycle():
    global last_vol_update_time, cached_vol_leaders
    logger.info("=" * 60)
    logger.info(f"🚀 MAINTAINER CYCLE START: {datetime.now(timezone.utc)}")
    logger.info("=" * 60)

    db = get_db()
    
    # 1. Fetch active subscriptions to build watchlist
    subs_rows = list(db.synap_surf_ai.find({"status": "ACTIVE"}, {"asset_name": 1}))
    active_assets = list(set([s.get("asset_name") for s in subs_rows if s.get("asset_name") and s.get("asset_name") != "AUTO"]))

    # 2. Build Master Watchlist
    current_time = time.time()
    if current_time - last_vol_update_time >= 7200 or not cached_vol_leaders:
        logger.info("Updating top volatility coins (runs every 2 hours)...")
        cached_vol_leaders = market_data.get_top_volatility_coins(limit=10)
        last_vol_update_time = current_time

    master_watchlist = list(set(cached_vol_leaders + CORE_WATCHLIST + active_assets))
    
    logger.info(f"Master Watchlist ({len(master_watchlist)} coins): {master_watchlist}")
    
    # Save the master watchlist to DB for the frontend to read
    try:
        db.market_data.update_one(
            {"key": "active_watchlist"},
            {"$set": {"value_json": json.dumps(master_watchlist)}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Failed to save active_watchlist: {e}")

    # 3. Fetch Free Global Intelligence
    logger.info("Fetching Technicals & Prices...")
    technicals = {}
    for coin in master_watchlist:
        try:
            mtf = market_data.get_mtf_technicals(coin)
            if mtf:
                technicals[coin] = mtf
        except Exception as e:
            logger.warning(f"Failed to get technicals for {coin}: {e}")
    
    logger.info("Fetching News Sentiment...")
    sentiment_data = news_sentiment.build_sentiment_data(master_watchlist)
    
    logger.info("Fetching Funding Rates...")
    funding_rates = market_data.get_all_funding_rates()

    # Package into market intelligence
    intel = {
        "technicals": technicals,
        "sentiment": sentiment_data,
        "funding_rates": funding_rates,
        "watchlist": master_watchlist
    }

    # Save to MongoDB for runner.py to read
    try:
        db.market_data.update_one(
            {"key": "market_intelligence"},
            {"$set": {"value_json": json.dumps(intel)}},
            upsert=True
        )
        logger.info("✅ Saved free market intelligence to database.")
    except Exception as e:
        logger.error(f"Failed to save market intelligence: {e}")

    logger.info(f"Cycle complete. Sleeping for {MAINTAINER_INTERVAL // 60} minutes.")

if __name__ == "__main__":
    while True:
        try:
            run_maintainer_cycle()
        except Exception as e:
            logger.error(f"Maintainer encountered a fatal error: {e}")
        time.sleep(MAINTAINER_INTERVAL)
