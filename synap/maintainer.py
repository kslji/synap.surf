import os
import sys
import json
import time
import logging
import uuid
import subprocess
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from synap.config import CORE_WATCHLIST
from synap import market_data
from synap import nansen_client
from synap import news_sentiment
from synap import claude_brain
from backend.db import get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s | Maintainer | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# How often to run the global AI evaluation (in seconds)
MAINTAINER_INTERVAL = 1800 # 30 Minutes

last_vol_update_time = 0
cached_vol_leaders = []

def run_maintainer_cycle():
    global last_vol_update_time, cached_vol_leaders
    logger.info("=" * 60)
    logger.info(f"🚀 MAINTAINER CYCLE START: {datetime.now(timezone.utc)}")
    logger.info("=" * 60)

    # 1. Fetch all active users and subscriptions
    with get_db() as db:
        users_rows = db.execute("SELECT wallet_address FROM users").fetchall()
        users = [u["wallet_address"] for u in users_rows]
        
        subs_rows = db.execute("SELECT DISTINCT asset_name FROM subscriptions WHERE status = 'ACTIVE'").fetchall()
        active_assets = [s["asset_name"] for s in subs_rows]

    if not users:
        logger.info("No users registered. Sleeping...")
        return

    # 2. Build Master Watchlist
    current_time = time.time()
    if current_time - last_vol_update_time >= 7200 or not cached_vol_leaders:
        logger.info("Updating top volatility coins (runs every 2 hours)...")
        cached_vol_leaders = market_data.get_top_volatility_coins(limit=10)
        last_vol_update_time = current_time

    master_watchlist = list(set(cached_vol_leaders + CORE_WATCHLIST + active_assets))
    
    logger.info(f"Master Watchlist ({len(master_watchlist)} coins): {master_watchlist}")

    # 3. Fetch Global Intelligence (Call external APIs ONCE to save cost!)
    logger.info("Fetching Technicals & Prices...")
    technicals = market_data.get_technical_analysis(master_watchlist)
    prices = market_data.get_mid_prices()
    
    logger.info("Fetching Nansen Smart Money Intelligence...")
    nansen_data = nansen_client.build_nansen_intelligence(master_watchlist)
    
    logger.info("Fetching News Sentiment...")
    sentiment_data = news_sentiment.build_sentiment_data(master_watchlist)
    
    funding_rates = market_data.get_all_funding_rates()

    # Empty mock portfolio for global scan
    global_portfolio = {"total_value": 0, "free_collateral": 0, "positions": []}

    # 4. Call Claude AI
    logger.info("Consulting Claude AI for Master Decision...")
    master_decision = claude_brain.get_ai_decision(
        technicals=technicals,
        sentiment_data=sentiment_data,
        nansen_data=nansen_data,
        portfolio=global_portfolio,
        funding_rates=funding_rates,
        watchlist=master_watchlist
    )

    if not master_decision:
        logger.warning("Claude failed to return a valid master decision. Aborting cycle.")
        return
        
    validated_decision = claude_brain.validate_decision(master_decision)
    logger.info(f"AI Market View: {validated_decision.get('market_assessment', 'None')}")

    # Save Master Decision to market_data so the Dashboard can display it for everyone!
    try:
        with get_db() as db:
            from backend.db import set_market_data
            set_market_data("market_intelligence_global", validated_decision)
    except Exception as e:
        logger.error(f"Failed to save global market intelligence: {e}")

    # 5. Group Users into Pools & Spawn PM2 Executors
    POOL_SIZE = 5
    pools = [users[i:i + POOL_SIZE] for i in range(0, len(users), POOL_SIZE)]
    
    logger.info(f"Splitting {len(users)} users into {len(pools)} pools.")
    
    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "tmp_payloads"))
    os.makedirs(temp_dir, exist_ok=True)

    for i, pool_wallets in enumerate(pools):
        payload_id = uuid.uuid4().hex[:8]
        payload_path = os.path.join(temp_dir, f"pool_{payload_id}.json")
        
        payload = {
            "wallets": pool_wallets,
            "master_decision": validated_decision
        }
        
        with open(payload_path, "w") as f:
            json.dump(payload, f)
            
        process_name = f"algo_executor_{payload_id}"
        executor_script = os.path.join(os.path.dirname(__file__), "executor.py")
        
        logger.info(f"Spawning PM2 process: {process_name} for Pool {i+1} ({len(pool_wallets)} wallets)")
        
        # Start PM2 with --no-autorestart so it dies cleanly after executing trades
        cmd = [
            "pm2", "start", executor_script,
            "--name", process_name,
            "--no-autorestart",
            "--", payload_path
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Failed to spawn PM2 process {process_name}: {e}")

    logger.info(f"Cycle complete. Sleeping for {MAINTAINER_INTERVAL // 60} minutes.")

if __name__ == "__main__":
    while True:
        try:
            run_maintainer_cycle()
        except Exception as e:
            logger.error(f"Maintainer encountered a fatal error: {e}")
        time.sleep(MAINTAINER_INTERVAL)
