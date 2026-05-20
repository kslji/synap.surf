import time
import argparse
from db import get_db

def run_strategy(strategy_id: str):
    """
    Template for PM2 strategy processes.
    In production, this connects to Hyperliquid WS or polls candles,
    evaluates technical indicators, and writes signals to the DB.
    """
    print(f"Starting PM2 runner for strategy: {strategy_id}")
    
    # Example logic skeleton
    while True:
        try:
            # 1. Fetch market data
            # 2. Evaluate indicator conditions
            # 3. If signal generated:
            #     with get_db() as db:
            #         db.execute("INSERT INTO signals_queue (strategy_id, coin, action, price) VALUES (?, ?, ?, ?)", (strategy_id, "BTC", "OPEN_LONG", 65000))
            
            time.sleep(10) # Poll interval
        except Exception as e:
            print(f"Error in strategy {strategy_id}: {e}")
            time.sleep(10)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", type=str, required=True)
    args = parser.parse_args()
    run_strategy(args.strategy)
