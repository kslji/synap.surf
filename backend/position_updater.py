import time
import logging
import sys
import os
from pathlib import Path

# Add parent to path to import synap
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from synap.paper_trader import PaperTrader
from synap.market_data import get_mid_prices

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("synap/logs/position_updater.log")
    ]
)
logger = logging.getLogger(__name__)

def update_positions_service():
    """
    Background service to update current prices and unrealized P&L 
    for open positions every few seconds.
    """
    logger.info("Position Update Service started (Every 5 seconds)")
    
    while True:
        try:
            # 1. Load current trader state
            trader = PaperTrader()
            
            if not trader.positions:
                # No open positions, nothing to update
                time.sleep(10)
                continue
                
            # 2. Fetch latest mid prices from Hyperliquid
            prices = get_mid_prices()
            
            if not prices:
                logger.warning("Failed to fetch mid prices, retrying...")
                time.sleep(5)
                continue
                
            # 3. Update trader with new prices (this also saves to portfolio_state.json)
            trader.update_prices(prices)
            
            # Log progress
            pos_names = [p['coin'] for p in trader.positions]
            logger.info(f"Updated prices for: {', '.join(pos_names)}")
            
        except Exception as e:
            logger.error(f"Error in position updater cycle: {e}")
            
        # Sleep for 5 seconds for "instant" feel without overwhelming the API
        time.sleep(5)

if __name__ == "__main__":
    try:
        update_positions_service()
    except KeyboardInterrupt:
        logger.info("Position Update Service stopped by user.")
