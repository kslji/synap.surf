import time
import os
import sys
import re

# Ensure project root is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.database import get_sync_db
from synap.hyperliquid_trader import HyperliquidTrader

def execute_signal_for_users(strategy_id: str, coin: str, action: str, price: float = None):
    """
    Executes trades for all ACTIVE users of a given strategy.
    Handles the transition of WAITING users to ACTIVE on CLOSE.
    """
    db = get_sync_db()
    
    if "OPEN" in action:
        # Update strategy state to IN_TRADE
        direction = "LONG" if "LONG" in action else "SHORT"
        db.strategy_state.update_one(
            {"strategy_id": strategy_id},
            {"$set": {"status": "IN_TRADE", "active_coin": coin, "active_direction": direction}},
            upsert=True
        )
        
        # Fetch all ACTIVE users
        subs = list(db.synap_surf_ai.find({"strategy_id": strategy_id, "status": "ACTIVE"}))
        
        for sub in subs:
            wallet_address = sub.get("wallet_address")
            if not wallet_address:
                continue
            
            user = db.users.find_one({"wallet_address": re.compile(f"^{wallet_address}$", re.IGNORECASE)})
            if not user or not user.get("private_key"):
                print(f"Skipping {wallet_address} - no private key")
                continue
            
            # Check user specific asset constraint
            u_asset = sub.get("asset_name", "AUTO")
            if u_asset != "AUTO" and u_asset.upper() != coin.upper():
                print(f"Skipping {wallet_address} - chose {u_asset}, not {coin}")
                continue
                
            capital = sub.get("capital", 1000)
            leverage = sub.get("leverage", 1)
            
            print(f"Executing {action} on {coin} for user {wallet_address} with capital {capital} and leverage {leverage}")
            try:
                trader = HyperliquidTrader(private_key=user['private_key'], wallet_address=wallet_address)
                
                target_pct = float(sub.get("target_pct") or 5.0)
                stop_loss_pct = float(sub.get("stop_loss_pct") or 5.0)
                
                if direction == "LONG":
                    sl = price * (1 - (stop_loss_pct / 100))
                    tp1 = price * (1 + (target_pct / 100))
                else:
                    sl = price * (1 + (stop_loss_pct / 100))
                    tp1 = price * (1 - (target_pct / 100))
                
                trader.open_position(
                    coin=coin,
                    side=direction,
                    entry_price=price or 0.0,
                    size_usd=capital * leverage,
                    leverage=leverage,
                    stop_loss=sl,
                    tp1=tp1,
                    tp2=tp1, # We will update this later with native Hyperliquid orders
                    conviction=0.8,
                    reasoning=f"AI Signal: {action} {coin}"
                )
            except Exception as e:
                print(f"Failed to execute for {wallet_address}: {e}")
            
    elif "CLOSE" in action:
        # Update strategy state to FLAT
        db.strategy_state.update_one(
            {"strategy_id": strategy_id},
            {"$set": {"status": "FLAT", "active_coin": None, "active_direction": None}},
            upsert=True
        )
        
        # Fetch all ACTIVE users and close their positions
        subs = list(db.synap_surf_ai.find({"strategy_id": strategy_id, "status": "ACTIVE"}))
        for sub in subs:
            wallet_address = sub.get("wallet_address")
            if not wallet_address:
                continue
                
            user = db.users.find_one({"wallet_address": re.compile(f"^{wallet_address}$", re.IGNORECASE)})
            if not user or not user.get("private_key"):
                continue
                
            print(f"Executing CLOSE on {coin} for user {wallet_address}")
            try:
                trader = HyperliquidTrader(private_key=user['private_key'], wallet_address=wallet_address)
                trader.close_position(coin, price or 0.0, reason=f"AI Signal: {action}")
            except Exception as e:
                print(f"Failed to close for {wallet_address}: {e}")
        
        # Now upgrade WAITING users to ACTIVE because the strategy is flat
        db.synap_surf_ai.update_many(
            {"strategy_id": strategy_id, "status": "WAITING"},
            {"$set": {"status": "ACTIVE"}}
        )
        print(f"Upgraded waiting users to ACTIVE for strategy {strategy_id}")

def engine_loop():
    print("Starting Execution Engine...")
    while True:
        try:
            db = get_sync_db()
            # Fetch unprocessed signals
            signals = list(db.signals_queue.find({"processed": 0}).sort("created_at", 1))
            
            for sig in signals:
                print(f"Processing Signal: {sig.get('action')} on {sig.get('coin')} from {sig.get('strategy_id')}")
                execute_signal_for_users(sig.get('strategy_id'), sig.get('coin'), sig.get('action'), sig.get('price'))
                
                # Mark as processed
                db.signals_queue.update_one({"_id": sig["_id"]}, {"$set": {"processed": 1}})
        
            time.sleep(1) # Poll interval
        except Exception as e:
            print(f"Error in execution engine: {e}")
            time.sleep(1)

if __name__ == "__main__":
    engine_loop()
