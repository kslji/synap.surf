#!/usr/bin/env python3
"""
synap/nansen_updater.py — Dedicated Nansen Cache Service

Runs every 4 hours. Calls Nansen API and writes results to db.nansen_cache.
This is the ONLY service that is allowed to burn Nansen API credits.
All other services (runner.py) read from nansen_cache and never call Nansen directly.
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from synap import nansen_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | NansenUpdater | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Refresh every 4 hours
NANSEN_REFRESH_INTERVAL = 14400


def run_nansen_update():
    logger.info("=" * 60)
    logger.info(f"🔷 NANSEN UPDATE START: {datetime.now(timezone.utc)}")
    logger.info("=" * 60)

    # 1. Perp Screener (1 credit) — writes to nansen_cache automatically
    try:
        logger.info("📡 Fetching Perp Screener...")
        result = nansen_client.get_perp_screener()
        logger.info(f"✅ Perp Screener: {'OK' if result else 'Empty'}")
    except Exception as e:
        logger.error(f"❌ Perp Screener failed: {e}")

    # 2. Smart Money Netflow for all coins (1 credit, fetches all at once)
    # We call get_smart_money_netflows for a broad coin to populate the shared cache
    try:
        logger.info("📡 Fetching Smart Money Netflow (bulk)...")
        # This populates the sm_netflow_all_24h cache key in the DB
        result = nansen_client.get_smart_money_netflows("BTC")  # BTC triggers bulk fetch + DB write
        logger.info(f"✅ Smart Money Netflow: {'OK' if result else 'Empty'}")
    except Exception as e:
        logger.error(f"❌ Smart Money Netflow failed: {e}")

    # 3. Token Screener (1 credit)
    try:
        logger.info("📡 Fetching Token Screener...")
        result = nansen_client.get_token_screener()
        logger.info(f"✅ Token Screener: {'OK' if result else 'Empty'}")
    except Exception as e:
        logger.error(f"❌ Token Screener failed: {e}")

    # 4. Meme Coin Data (1 credit)
    try:
        logger.info("📡 Fetching Meme Coin Data...")
        result = nansen_client.get_meme_coin_data()
        logger.info(f"✅ Meme Coin Data: {'OK' if result else 'Empty'}")
    except Exception as e:
        logger.error(f"❌ Meme Coin Data failed: {e}")

    logger.info(f"🏁 Nansen update complete. Next refresh in {NANSEN_REFRESH_INTERVAL // 3600} hours.")


if __name__ == "__main__":
    while True:
        try:
            run_nansen_update()
        except Exception as e:
            logger.error(f"Fatal error in Nansen updater: {e}")
        logger.info(f"💤 Sleeping {NANSEN_REFRESH_INTERVAL // 3600}h until next update...")
        time.sleep(NANSEN_REFRESH_INTERVAL)
