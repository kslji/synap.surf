import os
import sys
import time
import asyncio
import logging
from datetime import datetime
from pymongo import DESCENDING

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from backend.database import get_sync_db
from synap.hyperliquid_trader import HyperliquidTrader
from synap.market_data import fetch_candles

logging.basicConfig(level=logging.INFO, format="%(asctime)s | StrategyEngine | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

def get_strategy_class(strategy_id):
    import importlib.util
    import inspect
    from pathlib import Path
    
    lib_path = Path(__file__).resolve().parent.parent / "strategies_lib"
    strategy_file = lib_path / f"{strategy_id}.py"
    if not strategy_file.exists():
        return None
        
    if str(lib_path) not in sys.path:
        sys.path.insert(0, str(lib_path))
        
    spec = importlib.util.spec_from_file_location("dynamic_strategy", str(strategy_file))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if hasattr(obj, "run") and obj.__module__ == "dynamic_strategy":
            return obj
    return None

async def run_strategy_engine():
    logger.info("Starting Technical Strategy Execution Engine...")
    
    while True:
        try:
            db = get_sync_db()
            # 1. Fetch active subscriptions for technical strategies
            subs = list(db.synap_surf_ai.find({"status": "ACTIVE", "strategy_id": {"$ne": "ALGO AI BOT"}}))
            
            if not subs:
                await asyncio.sleep(5)
                continue
                
            # Group by (strategy_id, coin, timeframe)
            groups = {}
            for sub in subs:
                coin = sub.get("asset_name") or sub.get("coin", "BTC")
                key = (sub["strategy_id"], coin, sub.get("timeframe", "1h"))
                if key not in groups:
                    groups[key] = []
                groups[key].append(sub)
                
            for (strategy_id, coin, timeframe), users in groups.items():
                StrategyClass = get_strategy_class(strategy_id)
                if not StrategyClass:
                    logger.error(f"Strategy {strategy_id} not found.")
                    continue
                    
                tf_candles = {'1m': 100, '5m': 100, '15m': 100, '1h': 100, '4h': 100, '1d': 100}
                n_candles = tf_candles.get(timeframe, 100)
                
                df = fetch_candles(coin, interval=timeframe, n=n_candles)
                if df is None or df.empty:
                    continue
                    
                # We just run with default capital to get the signals
                strat_inst = StrategyClass(initial_capital=1000)
                try:
                    res = strat_inst.run(df)
                except Exception as e:
                    logger.error(f"Error running {strategy_id}: {e}")
                    continue
                    
                trade_log = res.get("trade_log", [])
                
                # Determine strategy's current desired position
                target_position = 0 # 0=FLAT, 1=LONG, -1=SHORT
                if trade_log:
                    last_trade = trade_log[-1]
                    if last_trade.get("reason") == "end_of_data":
                        target_position = 1 if last_trade.get("position") == 1 else -1

                # Now process for each user
                for user in users:
                    wallet = user["wallet_address"]
                    
                    # Get user's current open position for this strategy
                    db_pos = db.trade_logs.find_one({
                        "wallet_address": wallet,
                        "strategy_id": strategy_id,
                        "coin": coin,
                        "status": "OPEN"
                    }, sort=[("timestamp", DESCENDING)])
                    
                    current_position = 0
                    if db_pos:
                        current_position = 1 if db_pos["side"] == "LONG" else -1
                        
                    user_doc = db.users.find_one({"wallet_address": wallet})
                    if not user_doc or not user_doc.get("private_key"):
                        continue
                        
                    trader = HyperliquidTrader(private_key=user_doc["private_key"], wallet_address=wallet)
                    
                    # Logic 1: We need to CLOSE if current position doesn't match target
                    if current_position != 0 and current_position != target_position:
                        logger.info(f"[{wallet}] Strategy {strategy_id} closing {db_pos['side']} on {coin}")
                        try:
                            # Current market price for close
                            close_px = df.iloc[-1]["close"]
                            trader.close_position(coin=coin, current_price=close_px, reason="Technical Strategy Signal: Close")
                            
                            # Mark in DB
                            db.trade_logs.update_one({"_id": db_pos["_id"]}, {"$set": {"status": "CLOSED"}})
                            
                            # Log the exit
                            db.trade_logs.insert_one({
                                "wallet_address": wallet,
                                "event": "TRADE_CLOSE",
                                "strategy_id": strategy_id,
                                "coin": coin,
                                "side": db_pos["side"],
                                "entry_price": close_px,
                                "timestamp": datetime.utcnow().isoformat(),
                                "status": "EXECUTED",
                                "action": "BOT",
                            })
                            current_position = 0
                        except Exception as e:
                            logger.error(f"Error closing pos for {wallet}: {e}")
                            
                    # Logic 2: We need to OPEN if target is active and we are flat
                    if current_position == 0 and target_position != 0:
                        side = "LONG" if target_position == 1 else "SHORT"

                        # Require user-defined TP and SL before executing any trade
                        tp_pct = user.get("target_pct")
                        sl_pct = user.get("stop_loss_pct")
                        if not tp_pct or not sl_pct or float(tp_pct) <= 0 or float(sl_pct) <= 0:
                            logger.warning(
                                f"[{wallet}] Strategy {strategy_id}: TP/SL not configured — skipping trade. "
                                f"User must set Take Profit and Stop Loss before execution."
                            )
                            continue

                        capital = user.get("capital", 100)
                        leverage = user.get("leverage", 1)
                        margin_mode = user.get("margin_mode", "cross")
                        nominal_size = float(capital) * int(leverage)

                        entry_px = df.iloc[-1]["close"]
                        tp_dec = float(tp_pct) / 100.0
                        sl_dec = float(sl_pct) / 100.0
                        if side == "LONG":
                            tp_price = entry_px * (1 + tp_dec)
                            sl_price = entry_px * (1 - sl_dec)
                        else:
                            tp_price = entry_px * (1 - tp_dec)
                            sl_price = entry_px * (1 + sl_dec)

                        logger.info(
                            f"[{wallet}] Strategy {strategy_id} opening {side} on {coin} | "
                            f"entry={entry_px:.4f} TP={tp_price:.4f} (+{tp_pct}%) SL={sl_price:.4f} (-{sl_pct}%)"
                        )

                        try:
                            res = trader.open_position(
                                coin=coin,
                                side=side,
                                entry_price=entry_px,
                                size_usd=nominal_size,
                                leverage=int(leverage),
                                stop_loss=sl_price,
                                tp1=tp_price,
                                tp2=0.0,
                                conviction=1.0,
                                reasoning=f"Technical Strategy Entry: {strategy_id}",
                                margin_mode=margin_mode
                            )
                            
                            if res:
                                db.trade_logs.insert_one({
                                    "user_id": wallet,
                                    "wallet_address": wallet,
                                    "event": "TRADE_OPEN",
                                    "strategy_id": strategy_id,
                                    "coin": coin,
                                    "side": side,
                                    "entry_price": entry_px,
                                    "take_profit": tp_price,
                                    "stop_loss": sl_price,
                                    "target_pct": float(tp_pct),
                                    "stop_loss_pct": float(sl_pct),
                                    "position_size_usd": nominal_size,
                                    "size_usd": nominal_size,
                                    "leverage": int(leverage),
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "status": "OPEN",
                                    "action": "BOT",
                                })
                        except Exception as e:
                            logger.error(f"Error opening pos for {wallet}: {e}")

        except Exception as e:
            logger.error(f"Strategy Engine loop error: {e}")
            
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_strategy_engine())
