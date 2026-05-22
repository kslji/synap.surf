import time
import os
import sys

# Ensure project root is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.db import get_db
from synap.hyperliquid_trader import HyperliquidTrader

def execute_signal_for_users(strategy_id: str, coin: str, action: str, price: float = None):
    """
    Executes trades for all ACTIVE users of a given strategy.
    Handles the transition of WAITING users to ACTIVE on CLOSE.
    """
    with get_db() as db:
        if "OPEN" in action:
            # Update strategy state to IN_TRADE
            direction = "LONG" if "LONG" in action else "SHORT"
            db.execute("UPDATE strategy_state SET status = 'IN_TRADE', active_coin = ?, active_direction = ? WHERE strategy_id = ?", 
                       (coin, direction, strategy_id))
            
            # Fetch all ACTIVE users
            users = db.execute("SELECT s.*, u.private_key FROM subscriptions s JOIN users u ON LOWER(s.wallet_address) = LOWER(u.wallet_address) WHERE s.strategy_id = ? AND s.status = 'ACTIVE'", (strategy_id,)).fetchall()
            
            for user in users:
                if not user["private_key"]:
                    print(f"Skipping {user['wallet_address']} - no private key")
                    continue
                
                # Check user specific asset constraint
                u_asset = user.get("asset_name", "AUTO")
                if u_asset != "AUTO" and u_asset.upper() != coin.upper():
                    print(f"Skipping {user['wallet_address']} - chose {u_asset}, not {coin}")
                    continue
                    
                print(f"Executing {action} on {coin} for user {user['wallet_address']} with capital {user['capital']} and leverage {user['leverage']}")
                try:
                    trader = HyperliquidTrader(private_key=user['private_key'], wallet_address=user['wallet_address'])
                    
                    target_pct = float(user.get("target_pct") or 5.0)
                    stop_loss_pct = float(user.get("stop_loss_pct") or 5.0)
                    
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
                        size_usd=user['capital'] * user['leverage'],
                        leverage=user['leverage'],
                        stop_loss=sl,
                        tp1=tp1,
                        tp2=tp1, # We will update this later with native Hyperliquid orders
                        conviction=0.8,
                        reasoning=f"AI Signal: {action} {coin}"
                    )
                except Exception as e:
                    print(f"Failed to execute for {user['wallet_address']}: {e}")
                
        elif "CLOSE" in action:
            # Update strategy state to FLAT
            db.execute("UPDATE strategy_state SET status = 'FLAT', active_coin = NULL, active_direction = NULL WHERE strategy_id = ?", (strategy_id,))
            
            # Fetch all ACTIVE users and close their positions
            users = db.execute("SELECT s.*, u.private_key FROM subscriptions s JOIN users u ON LOWER(s.wallet_address) = LOWER(u.wallet_address) WHERE s.strategy_id = ? AND s.status = 'ACTIVE'", (strategy_id,)).fetchall()
            for user in users:
                if not user["private_key"]:
                    continue
                print(f"Executing CLOSE on {coin} for user {user['wallet_address']}")
                try:
                    trader = HyperliquidTrader(private_key=user['private_key'], wallet_address=user['wallet_address'])
                    trader.close_position(coin, price or 0.0, reason=f"AI Signal: {action}")
                except Exception as e:
                    print(f"Failed to close for {user['wallet_address']}: {e}")
            
            # Now upgrade WAITING users to ACTIVE because the strategy is flat
            db.execute("UPDATE subscriptions SET status = 'ACTIVE' WHERE strategy_id = ? AND status = 'WAITING'", (strategy_id,))
            print(f"Upgraded waiting users to ACTIVE for strategy {strategy_id}")

def engine_loop():
    print("Starting Execution Engine...")
    while True:
        try:
            with get_db() as db:
                # Fetch unprocessed signals
                signals = db.execute("SELECT * FROM signals_queue WHERE processed = 0 ORDER BY created_at ASC").fetchall()
                
                for sig in signals:
                    print(f"Processing Signal: {sig['action']} on {sig['coin']} from {sig['strategy_id']}")
                    execute_signal_for_users(sig['strategy_id'], sig['coin'], sig['action'], sig['price'])
                    
                    # Mark as processed
                    db.execute("UPDATE signals_queue SET processed = 1 WHERE id = ?", (sig['id'],))
            
            time.sleep(1) # Poll interval
        except Exception as e:
            print(f"Error in execution engine: {e}")
            time.sleep(1)

if __name__ == "__main__":
    engine_loop()
