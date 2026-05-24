import os
import sys
import json
import time
import logging
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
    
    # Watchlist = strictly top 10 most volatile Hyperliquid assets by 24h % move.
    # Refresh every 30 minutes so we always track the freshest movers.
    current_time = time.time()
    if current_time - last_vol_update_time >= 1800 or not cached_vol_leaders:
        logger.info("🔥 Refreshing top-10 volatility leaders from Hyperliquid (30-min cycle)...")
        cached_vol_leaders = market_data.get_top_volatility_coins(limit=10)
        last_vol_update_time = current_time

    # Strict: only the volatility top-10. No additions.
    master_watchlist = cached_vol_leaders[:10]

    logger.info(f"🎯 Trading Universe — Top 10 Volatile: {master_watchlist}")
    
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
