import os
import sys
import time
import asyncio
import logging
from datetime import datetime, timezone
from pymongo import MongoClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from backend.database import get_sync_db
from synap.hyperliquid_trader import HyperliquidTrader

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

async def execute_trade_for_user(user, signal):
    try:
        wallet = user.get('wallet_address')
        user_margin_pref = user.get('capital', 'AUTO')
        user_leverage_pref = user.get('leverage', 'AUTO')
        
        # Default AI sizes from the signal
        ai_position_size_pct = signal.get('position_size_pct', 0.05)
        ai_leverage = signal.get('leverage', 5)
        
        # Dummy balance for illustration:
        user_real_balance = 1000.0  
        
        # Determine actual Margin
        if user_margin_pref == 'AUTO':
            user_margin = user_real_balance * ai_position_size_pct
            logger.info(f"🤖 AUTO MARGIN for {wallet}: AI chose ${user_margin:.2f} ({ai_position_size_pct*100}%)")
        else:
            user_margin = float(user_margin_pref)
            logger.info(f"⚙️ MANUAL MARGIN for {wallet}: User set ${user_margin:.2f}")

        # Determine actual Leverage
        if user_leverage_pref == 'AUTO':
            user_leverage = ai_leverage
            logger.info(f"🤖 AUTO LEVERAGE for {wallet}: AI chose {user_leverage}x")
        else:
            user_leverage = int(user_leverage_pref)
            logger.info(f"⚙️ MANUAL LEVERAGE for {wallet}: User set {user_leverage}x")

        # Determine Stop Loss (SL) Price
        user_sl_pref = user.get('stop_loss_pct', 'AUTO')
        ai_sl_price = signal.get('stop_loss')
        entry_price = signal.get('entry_price', 0)
        side = signal.get('side', 'LONG')
        
        if user_sl_pref == 'AUTO' or user_sl_pref is None:
            final_sl_price = ai_sl_price
            logger.info(f"🤖 AUTO SL for {wallet}: AI chose ${final_sl_price}")
        else:
            sl_pct = float(user_sl_pref) / 100.0
            if side == 'LONG':
                final_sl_price = entry_price * (1 - sl_pct)
            else:
                final_sl_price = entry_price * (1 + sl_pct)
            logger.info(f"⚙️ MANUAL SL for {wallet}: User set {user_sl_pref}% -> ${final_sl_price:.4f}")

        # Determine Take Profit (TP) Price
        user_tp_pref = user.get('target_pct', 'AUTO')
        ai_tp_price = signal.get('take_profit_1')
        
        if user_tp_pref == 'AUTO' or user_tp_pref is None:
            final_tp_price = ai_tp_price
            logger.info(f"🤖 AUTO TP for {wallet}: AI chose ${final_tp_price}")
        else:
            tp_pct = float(user_tp_pref) / 100.0
            if side == 'LONG':
                final_tp_price = entry_price * (1 + tp_pct)
            else:
                final_tp_price = entry_price * (1 - tp_pct)
            logger.info(f"⚙️ MANUAL TP for {wallet}: User set {user_tp_pref}% -> ${final_tp_price:.4f}")


        
        # Don't execute if margin is below $10 (Hyperliquid requirement)
        if user_margin < 10:
            logger.warning(f"Skipping {signal['coin']} for {wallet}: Margin ${user_margin:.2f} is below $10 minimum.")
            return

        nominal_size = user_margin * user_leverage
        
        logger.info(f"Executing {signal['side']} {signal['coin']} for user {wallet} | Margin: ${user_margin:.2f} | Lev: {user_leverage}x | Nominal: ${nominal_size:.2f}")
        
        # Initialize trader with user credentials and execute...
        await asyncio.sleep(0.1)
    except Exception as e:
        logger.error(f"Error executing trade for user {user.get('wallet_address')}: {e}")

async def process_signal(signal):
    logger.info(f"Processing signal: {signal['side']} {signal['coin']}")
    try:
        db = get_sync_db()
        # Get all active subscriptions
        users = list(db.synap_surf_ai.find({"status": "ACTIVE", "$or": [{"asset_name": signal['coin']}, {"asset_name": "AUTO"}]}))
        
        logger.info(f"Found {len(users)} subscribed users.")
        
        # In a real PM2 setup with multiple workers, we would chunk users
        # For now, execute asynchronously
        tasks = [execute_trade_for_user(user, signal) for user in users]
        await asyncio.gather(*tasks)
        
        # Mark signal as processed
        db.signals_queue.update_one({"_id": signal["_id"]}, {"$set": {"status": "PROCESSED"}})
            
    except Exception as e:
        logger.error(f"Error processing signal: {e}")

async def worker_loop():
    logger.info("Worker started. Polling signals_queue...")
    while True:
        try:
            db = get_sync_db()
            signal = db.signals_queue.find_one_and_update(
                {"status": "PENDING"},
                {"$set": {"status": "PROCESSING"}}
            )
            if signal:
                await process_signal(signal)
            else:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(worker_loop())
