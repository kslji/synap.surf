import asyncio
import logging
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from backend.database import get_async_db

logger = logging.getLogger("backend.services.trade_sync")

async def run_service():
    """Fetches user_fills from Hyperliquid to capture manual trades, runs every 5 minutes."""
    db = get_async_db()
    while True:
        try:
            from hyperliquid.info import Info
            from hyperliquid.utils import constants
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            
            # Fetch all users
            users = await db.users.find({}).to_list(length=None)
            wallet_addresses = [u.get("wallet_address") for u in users if u.get("wallet_address")]
                
            for wallet in wallet_addresses:
                if not wallet or not wallet.startswith('0x') or len(wallet) != 42:
                    continue
                try:
                    fills = await asyncio.to_thread(info.user_fills, wallet)
                    
                    if fills:
                        for fill in fills:
                            fill_time = fill.get("time", 0)
                            dt = datetime.fromtimestamp(fill_time / 1000, tz=timezone.utc)
                            
                            existing = await db.trade_logs.find_one({
                                "user_id": wallet,
                                "coin": fill["coin"],
                                "side": fill["dir"],
                                "timestamp": dt
                            })
                            
                            if not existing:
                                sz = float(fill.get("sz", 0))
                                px = float(fill.get("px", 0))
                                pnl = float(fill.get("closedPnl", 0))
                                
                                new_trade = {
                                    "user_id": wallet,
                                    "event": "FILL",
                                    "coin": fill["coin"],
                                    "side": fill["dir"],
                                    "entry_price": px,
                                    "exit_price": px if pnl != 0 else None,
                                    "pnl_usd": pnl if pnl != 0 else None,
                                    "position_size_usd": sz * px,
                                    "action": "MANUAL_OR_EXTERNAL_TRADE",
                                    "details": "Direct fill from exchange",
                                    "timestamp": dt
                                }
                                await db.trade_logs.insert_one(new_trade)
                except Exception as ex:
                    logger.error(f"Error fetching fills for {wallet}: {ex}")
        except Exception as e:
            logger.error(f"Error in trade_sync_service: {e}")
            
        await asyncio.sleep(300) # 5 minutes
