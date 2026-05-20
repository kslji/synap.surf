#!/usr/bin/env python3
import logging
import json
import time
from decimal import Decimal
from datetime import datetime, UTC
from typing import Optional, Dict, Any

from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants
from eth_account import Account

# ================= CONFIG =================
# !! SECURE YOUR KEYS !!
API_PRIVATE_KEY = "0x4b7b4a76ddd7dfb492be17d8fcb8396ed13ef8c1f4f320e3da51ff89488e0c47"
MAIN_WALLET_ADDRESS = "0x77Dab0eAEC92907acC4D5836e03eeFc50e655Ca5"

USE_TESTNET = False
MAX_LEVERAGE = 10

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class HyperliquidBot:
    def __init__(self):
        self.wallet = Account.from_key(API_PRIVATE_KEY)
        self.user_address = MAIN_WALLET_ADDRESS
        self.base_url = (
            constants.TESTNET_API_URL if USE_TESTNET else constants.MAINNET_API_URL
        )

        self.exchange = Exchange(
            self.wallet,
            base_url=self.base_url,
            account_address=self.user_address,
        )
        self.info = Info(base_url=self.base_url, skip_ws=True)

        logger.info(f"Bot initialized on {'TESTNET' if USE_TESTNET else 'MAINNET'}")
        logger.info(f"Trading Account: {self.user_address}")

    # ---------- PRICE & UTILS ----------
    def get_mid_price(self, coin: str) -> Decimal:
        coin = coin.upper()
        mids = self.info.all_mids()
        if coin not in mids:
            raise ValueError(f"No price available for {coin}")
        return Decimal(mids[coin])

    def calculate_size(self, coin: str, notional: Decimal, price: Decimal) -> str:
        meta = self.info.meta()
        for a in meta["universe"]:
            if a["name"] == coin.upper():
                decimals = a["szDecimals"]
                size = notional / price
                return f"{size:.{decimals}f}".rstrip("0").rstrip(".")
        raise ValueError(f"Coin {coin} not found")

    def set_leverage(self, coin: str, leverage: int):
        if not (1 <= leverage <= MAX_LEVERAGE):
            raise ValueError(f"Invalid leverage {leverage}")
        self.exchange.update_leverage(leverage, coin.upper(), True)

    # ---------- POSITION INFO ----------
    def get_position(self, coin: str) -> Optional[Dict[str, Any]]:
        """Fetches the active position data for a specific coin."""
        state = self.info.user_state(self.user_address)
        for p in state.get("assetPositions", []):
            if p["position"]["coin"] == coin.upper():
                return p["position"]
        return None

    # ---------- TRADING METHODS ----------
    def open_long(self, coin: str, notional: Decimal, leverage: Optional[int] = None):
        """Helper to execute a simple long order (Buy)."""
        return self.place_market_order(coin, notional, is_buy=True, leverage=leverage)

    def open_short(self, coin: str, notional: Decimal, leverage: Optional[int] = None):
        """Helper to execute a simple short order (Sell)."""
        return self.place_market_order(coin, notional, is_buy=False, leverage=leverage)

    def place_market_order(
        self, coin: str, notional: Decimal, is_buy: bool, leverage: Optional[int] = None
    ):
        coin = coin.upper()
        if leverage:
            self.set_leverage(coin, leverage)

        price = self.get_mid_price(coin)
        size = self.calculate_size(coin, notional, price)

        logger.info(
            f"Opening {'LONG' if is_buy else 'SHORT'} on {coin} with ${notional} notional"
        )

        try:
            result = self.exchange.market_open(
                name=coin,
                is_buy=is_buy,
                sz=float(size),
                px=float(price),
                slippage=0.02,
            )
            self._log_order(coin, size, is_buy, notional, result)
            return result
        except Exception as e:
            logger.error(f"Order failed: {e}")
            return None

    def close_position(self, coin: str, size: Optional[float] = None):
        """
        Closes a position (Long or Short).
        If size is None, it closes the entire position.
        """
        coin = coin.upper()
        try:
            # market_close detects if you are currently long or short
            # and places the correct opposite order automatically.
            result = self.exchange.market_close(coin=coin, sz=size, slippage=0.02)
            logger.info(f"Close result for {coin}: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to close {coin}: {e}")
            return None

    def _log_order(self, coin, size, is_buy, notional, result):
        log_data = {
            "time": datetime.now(UTC).isoformat(),
            "coin": coin,
            "is_buy": is_buy,
            "size": str(size),
            "notional": str(notional),
            "result": result,
        }
        filename = f"orders_{datetime.now(UTC).strftime('%Y%m%d')}.jsonl"
        with open(filename, "a") as f:
            f.write(json.dumps(log_data) + "\n")


# ================= EXAMPLE USAGE =================
# if __name__ == "__main__":
#     bot = HyperliquidBot()

# Example 1: Open a $15 SOL Long at 5x leverage
# bot.open_long("SOL", notional=Decimal("15"), leverage=5)
# time.sleep(2)
# bot.close_position("SOL") # Closes the long

# Example 2: Open a $200 SOL Short at 10x leverage
# bot.open_short("SOL", notional=Decimal("15"), leverage=10)
# time.sleep(5)
# bot.close_position("SOL")
