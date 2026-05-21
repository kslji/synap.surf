import os
import logging
from typing import Optional, Dict, Any, List

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

logger = logging.getLogger(__name__)

class HyperliquidManualClient:
    def __init__(self):
        # Read at runtime so Settings saves are reflected immediately
        private_key = os.environ.get("HL_PRIVATE_KEY", "").strip()
        wallet = os.environ.get("HL_WALLET", "").strip()

        if not private_key or not wallet:
            raise ValueError(
                "Hyperliquid credentials not configured. "
                "Go to Settings → Exchange Integration, enter your Private Key "
                "and connect your EVM wallet, then click 'Save & Connect'."
            )

        self.wallet = Account.from_key(private_key)
        self.user_address = wallet
        self.base_url = constants.MAINNET_API_URL

        self.exchange = Exchange(
            self.wallet,
            base_url=self.base_url,
            account_address=self.user_address,
        )
        self.info = Info(base_url=self.base_url, skip_ws=True)

    def _get_sz_decimals(self, coin: str) -> int:
        try:
            meta = self.info.meta()
            for asset in meta.get("universe", []):
                if asset["name"] == coin.upper():
                    return int(asset["szDecimals"])
        except Exception as e:
            logger.error(f"Error fetching szDecimals for {coin}: {e}")
        return 4

    def _calculate_size(self, coin: str, size_usd: float, price: float) -> float:
        decimals = self._get_sz_decimals(coin)
        size = size_usd / price
        rounded_size = float(f"{size:.{decimals}f}")
        return rounded_size
        
    def _get_current_price(self, coin: str) -> float:
        try:
            state = self.info.meta_and_asset_ctxs()
            meta, asset_ctxs = state
            for i, asset in enumerate(meta.get("universe", [])):
                if asset["name"] == coin.upper():
                    return float(asset_ctxs[i]["markPx"])
        except Exception as e:
            logger.error(f"Error fetching current price for {coin}: {e}")
        return 0.0

    def open_position(
        self,
        coin: str,
        side: str, # "LONG" or "SHORT"
        size_usd: float,
        leverage: int,
        is_limit: bool = False,
        limit_price: Optional[float] = None,
        sl_price: Optional[float] = None,
        tp_price: Optional[float] = None
    ) -> Dict[str, Any]:
        coin = coin.upper()
        is_buy = side == "LONG"
        
        # Set Leverage
        try:
            self.exchange.update_leverage(leverage, coin, True)
        except Exception as e:
            logger.error(f"Failed to set leverage for {coin}: {e}")
            return {"status": "error", "message": f"Failed to set leverage: {str(e)}"}

        current_px = self._get_current_price(coin)
        if current_px == 0.0:
            return {"status": "error", "message": f"Could not fetch price for {coin}"}
            
        sz = self._calculate_size(coin, size_usd, limit_price if is_limit and limit_price else current_px)
        
        result = None
        try:
            if is_limit and limit_price:
                result = self.exchange.order(coin, is_buy, sz, limit_price, {"limit": {"tif": "Gtc"}})
            else:
                result = self.exchange.market_open(name=coin, is_buy=is_buy, sz=sz, px=current_px, slippage=0.02)
                
            if result.get("status") == "ok":
                # Check for inner exchange errors
                try:
                    statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                    if statuses and "error" in statuses[0]:
                        return {"status": "error", "message": statuses[0]["error"]}
                except Exception:
                    pass

                # Handle TP / SL orders if requested
                # TP/SL requires submitting trigger orders
                # Note: For robust TP/SL, we submit trigger orders on the opposite side
                if sl_price or tp_price:
                    # In a real robust implementation, one would wait for fill or submit reduce-only triggers.
                    # We submit basic trigger orders here.
                    self.set_tp_sl(coin, not is_buy, sz, tp_price, sl_price)
                
                return {"status": "success", "result": result}
            else:
                return {"status": "error", "message": str(result)}
        except Exception as e:
            logger.error(f"Error opening position: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def set_tp_sl(self, coin: str, is_buy: bool, sz: float, tp_price: Optional[float], sl_price: Optional[float]):
        """Sets take profit and/or stop loss trigger orders."""
        coin = coin.upper()
        try:
            if tp_price:
                self.exchange.order(
                    coin, is_buy, sz, tp_price, 
                    {"trigger": {"triggerPx": tp_price, "isMarket": True, "tpsl": "tp"}},
                    reduce_only=True
                )
            if sl_price:
                self.exchange.order(
                    coin, is_buy, sz, sl_price, 
                    {"trigger": {"triggerPx": sl_price, "isMarket": True, "tpsl": "sl"}},
                    reduce_only=True
                )
        except Exception as e:
            logger.error(f"Error setting TP/SL: {e}", exc_info=True)

    def close_position(self, coin: str) -> Dict[str, Any]:
        coin = coin.upper()
        try:
            result = self.exchange.market_close(coin=coin, slippage=0.02)
            if result.get("status") == "ok":
                try:
                    statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                    if statuses and "error" in statuses[0]:
                        return {"status": "error", "message": statuses[0]["error"]}
                except Exception:
                    pass
                return {"status": "success", "result": result}
            else:
                return {"status": "error", "message": str(result)}
        except Exception as e:
            logger.error(f"Error closing position: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def reverse_position(self, coin: str) -> Dict[str, Any]:
        coin = coin.upper()
        try:
            # 1. Get current position details
            state = self.info.user_state(self.user_address)
            current_sz = 0.0
            is_currently_long = True
            
            for entry in state.get("assetPositions", []):
                p = entry.get("position", {})
                if p.get("coin") == coin:
                    szi = float(p.get("szi", 0))
                    current_sz = abs(szi)
                    is_currently_long = szi > 0
                    break
                    
            if current_sz == 0:
                return {"status": "error", "message": "No open position to reverse"}
                
            # 2. Close current
            close_res = self.exchange.market_close(coin=coin, slippage=0.02)
            if close_res.get("status") != "ok":
                return {"status": "error", "message": f"Failed to close before reverse: {close_res}"}
                
            # 3. Open opposite
            new_is_buy = not is_currently_long
            current_px = self._get_current_price(coin)
            
            open_res = self.exchange.market_open(name=coin, is_buy=new_is_buy, sz=current_sz, px=current_px, slippage=0.02)
            if open_res.get("status") == "ok":
                try:
                    statuses = open_res.get("response", {}).get("data", {}).get("statuses", [])
                    if statuses and "error" in statuses[0]:
                        return {"status": "error", "message": f"Closed successfully, but failed to open opposite: {statuses[0]['error']}"}
                except Exception:
                    pass
                return {"status": "success", "result": open_res}
            else:
                return {"status": "error", "message": f"Closed but failed to open new: {open_res}"}
                
        except Exception as e:
            logger.error(f"Error reversing position: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
