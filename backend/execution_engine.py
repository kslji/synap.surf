import time
from db import get_db

# Assume we have hyperliquid client logic
# from backend.hyperliquid_client import HyperliquidManualClient

def execute_signal_for_users(strategy_id: str, coin: str, action: str):
    """
    Executes trades for all ACTIVE users of a given strategy.
    Handles the transition of WAITING users to ACTIVE on CLOSE.
    """
    with get_db() as db:
        if "OPEN" in action:
            # Update strategy state to IN_TRADE
            db.execute("UPDATE strategy_state SET status = 'IN_TRADE', active_coin = ?, active_direction = ? WHERE strategy_id = ?", 
                       (coin, action.split('_')[1], strategy_id))
            
            # Fetch all ACTIVE users
            users = db.execute("SELECT wallet_address, capital, leverage FROM subscriptions WHERE strategy_id = ? AND status = 'ACTIVE'", (strategy_id,)).fetchall()
            
            for user in users:
                print(f"Executing {action} on {coin} for user {user['wallet_address']} with capital {user['capital']} and leverage {user['leverage']}")
                # Here we would initialize the Hyperliquid client using the user's private key
                # hl = HyperliquidManualClient(wallet=user['wallet_address'], private_key=db.get_private_key(user['wallet_address']))
                # hl.open_position(coin, action.split('_')[1], user['capital'], user['leverage'])
                
        elif "CLOSE" in action:
            # Update strategy state to FLAT
            db.execute("UPDATE strategy_state SET status = 'FLAT', active_coin = NULL, active_direction = NULL WHERE strategy_id = ?", (strategy_id,))
            
            # Fetch all ACTIVE users and close their positions
            users = db.execute("SELECT wallet_address FROM subscriptions WHERE strategy_id = ? AND status = 'ACTIVE'", (strategy_id,)).fetchall()
            for user in users:
                print(f"Executing CLOSE on {coin} for user {user['wallet_address']}")
                # hl.close_position(coin)
            
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
                    execute_signal_for_users(sig['strategy_id'], sig['coin'], sig['action'])
                    
                    # Mark as processed
                    db.execute("UPDATE signals_queue SET processed = 1 WHERE id = ?", (sig['id'],))
            
            time.sleep(1) # Poll interval
        except Exception as e:
            print(f"Error in execution engine: {e}")
            time.sleep(1)

if __name__ == "__main__":
    engine_loop()
