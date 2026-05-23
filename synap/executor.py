import os
import sys
import json
import logging
import time
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from synap.hyperliquid_trader import HyperliquidTrader
from synap.trade_journal import log_ai_decision
from backend.database import get_sync_db as get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s | Executor | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

def execute_pool(payload_path: str):
    """
    Reads the master payload (wallets + master decision)
    and executes trades asynchronously per wallet.
    """
    logger.info(f"Starting executor pool with payload: {payload_path}")
    try:
        with open(payload_path, "r") as f:
            payload = json.load(f)
            
        wallets = payload.get("wallets", [])
        master_decision = payload.get("master_decision", {})
        
        if not wallets:
            logger.warning("No wallets provided to executor.")
            return

        db = get_db()
        # Safely query users
        users = list(db.users.find({"wallet_address": {"$in": wallets}}, {"wallet_address": 1, "private_key": 1, "_id": 0}))
        
        # Pre-fetch all active synap_surf_ai for these wallets
        subs = list(db.synap_surf_ai.find({"status": "ACTIVE", "wallet_address": {"$in": wallets}}, {"wallet_address": 1, "asset_name": 1, "_id": 0}))
            
        # Group subscriptions by wallet
        wallet_subs = {w: [] for w in wallets}
        for sub in subs:
            wallet_subs[sub["wallet_address"]].append(sub["asset_name"])

        for user in users:
            wallet = user["wallet_address"]
            pkey = user["private_key"]
            if not pkey:
                logger.warning(f"Skipping {wallet} (no private key found).")
                continue
                
            user_assets = wallet_subs.get(wallet, [])
            if not user_assets:
                logger.info(f"Wallet {wallet} has no active subscriptions. Skipping execution.")
                continue

            logger.info(f"Processing wallet {wallet} (Subscribed to: {user_assets})")
            
            # 1. Filter Master Decision for this specific user's assets
            user_trades = [t for t in master_decision.get("trades", []) if t.get("coin") in user_assets]
            user_updates = [u for u in master_decision.get("position_updates", []) if u.get("coin") in user_assets]
            
            if not user_trades and not user_updates:
                logger.info(f"  No relevant AI signals for {wallet}.")
                continue
                
            user_decision = {
                "scan_result": master_decision.get("scan_result", {}),
                "market_assessment": master_decision.get("market_assessment", ""),
                "trades": user_trades,
                "position_updates": user_updates,
            }
            
            # 2. Log the personalized decision to DB (Mapped to wallet!)
            log_ai_decision(user_decision, user_id=wallet)
            logger.info(f"  Logged personalized AI decision for {wallet}.")

            # 3. Execute Trades
            try:
                trader = HyperliquidTrader(private_key=pkey, wallet_address=wallet)
                logger.info(f"  Authenticated trader for {wallet}.")
                
                # Apply SL/TP updates
                if user_updates:
                    current_prices = {u["coin"]: trader.info.all_mids().get(u["coin"]) for u in user_updates}
                    trader.apply_ai_updates(user_updates, current_prices)
                    logger.info(f"  Applied {len(user_updates)} position updates for {wallet}.")
                    
                # Execute new entries
                for trade in user_trades:
                    logger.info(f"  Executing {trade['side']} on {trade['coin']} for {wallet}...")
                    trader.execute_trade(trade)
                    
            except Exception as e:
                logger.error(f"  Trade execution failed for {wallet}: {e}")

    except Exception as e:
        logger.error(f"Executor failed: {e}")
        
    finally:
        # Cleanup payload file
        try:
            if os.path.exists(payload_path):
                os.remove(payload_path)
        except:
            pass
        logger.info("Executor finished. Exiting.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python3 executor.py <payload_path>")
        sys.exit(1)
        
    payload_file = sys.argv[1]
    execute_pool(payload_file)
