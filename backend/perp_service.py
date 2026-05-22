import time
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add parent to path to import synap
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from synap.market_data import get_top_3_perps_with_details

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / "synap" / "logs" / "top_perps.json"

def update_top_perps():
    """Fetch top perps and save to JSON file."""
    try:
        logger.info("Fetching top 3 volatile perps from Hyperliquid...")
        data = get_top_3_perps_with_details()
        
        # Add a timestamp so we know when it was last updated
        result = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        
        # Ensure directory exists
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(OUTPUT_FILE, "w") as f:
            json.dump(result, f, indent=2)
            
        logger.info(f"Successfully saved top perps to {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Error in perp service: {e}")

if __name__ == "__main__":
    logger.info("Perp Update Service started (Every 20 minutes)")
    while True:
        update_top_perps()
        # Sleep for 20 minutes
        time.sleep(20 * 60)
