#!/usr/bin/env python3
"""
algo_brain/hyperliquid_trader.py — Hyperliquid Live mainnet trading execution engine.

Handles:
  - Placing real market open and close orders on Hyperliquid.
  - Setting 10x leverage on entries automatically.
  - Calculating exact coin sizing based on asset universe decimals (szDecimals).
  - Syncing live open positions with local stop-loss/take-profit metadata.
  - Tracking accumulated fees and realized P&L.
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

from algo_brain.config import (
    HL_PRIVATE_KEY,
    HL_WALLET,
    HL_TAKER_FEE,
    HL_SLIPPAGE_RATE,
    MAX_OPEN_POSITIONS,
    MAX_HOLD_HOURS,
    MIN_ROE_EXIT_PCT,
)
from algo_brain import trade_journal
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from backend.db import get_db

logger = logging.getLogger(__name__)


class HyperliquidTrader:
    """
    Live trading execution engine.
    Performs real fills on Hyperliquid mainnet.
    Syncs with exchange user_state and local tracking JSON metadata.
    """

    def __init__(self):
        if not HL_PRIVATE_KEY or not HL_WALLET:
            raise ValueError(
                "HL_PRIVATE_KEY and HL_WALLET must be set in the .env file for Live Trading."
            )

        self.wallet = Account.from_key(HL_PRIVATE_KEY)
        self.user_address = HL_WALLET
        self.base_url = constants.MAINNET_API_URL

        self.exchange = Exchange(
            self.wallet,
            base_url=self.base_url,
            account_address=self.user_address,
        )
        self.info = Info(base_url=self.base_url, skip_ws=True)
        # Cumulative stats (persisted locally)
        self.realized_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_fees_paid = 0.0
        self.last_traded_token = ""

        self.current_prices = {}

        try:
            with get_db() as db:
                row = db.execute("SELECT * FROM portfolios WHERE user_id = ? AND portfolio_type = 'LIVE'", (self.user_address,)).fetchone()
                if row:
                    self.realized_pnl = row["realized_pnl"]
                    self.total_trades = row["total_trades"]
                    self.winning_trades = row["winning_trades"]
                    self.losing_trades = row["losing_trades"]
        except Exception as e:
            logger.error(f"Error loading live cumulative stats: {e}")

        logger.info(
            f"🟢 HyperliquidTrader initialized on MAINNET for account {self.user_address}"
        )

    # ── State Sync & Metadata Persistence ────────────────────────────────────

    def _load_local_state(self) -> List[Dict]:
        """Load open positions metadata from db."""
        try:
            with get_db() as db:
                kv_row = db.execute("SELECT value_json FROM market_data WHERE key = 'live_positions'").fetchone()
                if kv_row:
                    return json.loads(kv_row["value_json"])
        except Exception as e:
            logger.error(f"Error loading live portfolio state: {e}")
        return []

    def _save_local_state(self, positions: List[Dict]):
        """Save open positions and cumulative metrics to db."""
        try:
            with get_db() as db:
                db.execute('''
                    INSERT INTO portfolios (user_id, portfolio_type, cash, total_equity, unrealized_pnl, realized_pnl, total_trades, winning_trades, losing_trades)
                    VALUES (?, 'LIVE', ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, portfolio_type) DO UPDATE SET
                        cash=excluded.cash,
                        total_equity=excluded.total_equity,
                        unrealized_pnl=excluded.unrealized_pnl,
                        realized_pnl=excluded.realized_pnl,
                        total_trades=excluded.total_trades,
                        winning_trades=excluded.winning_trades,
                        losing_trades=excluded.losing_trades,
                        updated_at=CURRENT_TIMESTAMP
                ''', (
                    self.user_address,
                    round(self.cash, 2),
                    round(self.total_equity, 2),
                    round(sum(p.get("unrealized_pnl", 0) for p in positions), 2),
                    round(self.realized_pnl, 2),
                    self.total_trades,
                    self.winning_trades,
                    self.losing_trades
                ))
                
                db.execute('''
                    INSERT INTO market_data (key, value_json) VALUES ('live_positions', ?)
                    ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=CURRENT_TIMESTAMP
                ''', (json.dumps(positions, default=str),))
        except Exception as e:
            logger.error(f"Error saving live portfolio state: {e}")

    def _save_state(self):
        """Saves current live portfolio snapshot. Keeps compatibility with PaperTrader."""
        self._save_local_state(self.positions)

    # ── Portfolio Info ────────────────────────────────────────────────────────

    @property
    def cash(self) -> float:
        """Available withdrawable margin directly from Hyperliquid user_state."""
        try:
            state = self.info.user_state(self.user_address)
            return float(state.get("withdrawable", 0.0))
        except Exception as e:
            logger.error(f"Error fetching withdrawable cash: {e}")
            return 0.0

    @property
    def total_equity(self) -> float:
        """Total account value from Hyperliquid marginSummary."""
        try:
            state = self.info.user_state(self.user_address)
            margin_summary = state.get("marginSummary", {})
            return float(margin_summary.get("accountValue", 0.0))
        except Exception as e:
            logger.error(f"Error fetching account value: {e}")
            return 0.0

    @property
    def total_deployed(self) -> float:
        """Total capital deployed in open positions (margin used)."""
        return sum(
            p["size_usd"] / p["leverage"] * p["remaining_size_pct"]
            for p in self.positions
        )

    @property
    def deployed_pct(self) -> float:
        """Percentage of equity currently deployed."""
        eq = self.total_equity
        return self.total_deployed / eq if eq > 0 else 0.0

    @property
    def positions(self) -> List[Dict]:
        """
        Fetches active positions directly from the Hyperliquid API,
        cross-references with `portfolio_state_live.json` to attach local tracking metadata
        (Stop Loss, Take Profit targets, conviction, reasoning, opened_at).
        Also syncs local json to match the actual exchange state.
        """
        try:
            # 1. Fetch active perp positions from the exchange
            state = self.info.user_state(self.user_address)
            hl_positions = []
            for entry in state.get("assetPositions", []):
                pos = entry.get("position", {})
                if pos and float(pos.get("szi", 0)) != 0:
                    hl_positions.append(pos)

            # 2. Load our locally saved metadata
            local_positions = self._load_local_state()

            updated_positions = []
            local_by_coin = {p["coin"]: p for p in local_positions}

            # 3. Align local metadata with real exchange positions
            for hl_pos in hl_positions:
                coin = hl_pos["coin"]
                szi = float(hl_pos["szi"])
                side = "LONG" if szi > 0 else "SHORT"
                entry_px = float(hl_pos["entryPx"])
                unrealized_pnl = float(hl_pos["unrealizedPnl"])

                # Check if we already have local tracking metadata for this coin
                if coin in local_by_coin:
                    local_pos = local_by_coin[coin]
                    # Update parameters that might have changed on the exchange
                    local_pos["entry_price"] = entry_px
                    local_pos["size_usd"] = abs(szi) * entry_px
                    local_pos["unrealized_pnl"] = unrealized_pnl
                    # Calculate unrealized P&L % (ROE %) using leverage
                    leverage = local_pos.get("leverage", 10)
                    if entry_px > 0:
                        current_px = self.current_prices.get(coin, entry_px)
                        if side == "LONG":
                            local_pos["unrealized_pnl_pct"] = (
                                ((current_px / entry_px) - 1) * leverage * 100
                            )
                        else:
                            local_pos["unrealized_pnl_pct"] = (
                                (1 - (current_px / entry_px)) * leverage * 100
                            )
                    updated_positions.append(local_pos)
                else:
                    # Found a position on the exchange that is not in our local metadata (e.g. opened manually)
                    # We create a default tracking item for it so the bot doesn't crash or lose track
                    mid_px = self.current_prices.get(coin, entry_px)
                    # Establish sensible default stop/take-profit boundaries (5%, 5%, 10%)
                    if side == "LONG":
                        sl = entry_px * 0.985
                        tp1 = entry_px * 1.05
                        tp2 = entry_px * 1.10
                    else:
                        sl = entry_px * 1.015
                        tp1 = entry_px * 0.95
                        tp2 = entry_px * 0.90

                    new_pos = {
                        "coin": coin,
                        "side": side,
                        "entry_price": entry_px,
                        "size_usd": abs(szi) * entry_px,
                        "leverage": 10,  # assume 10x default
                        "stop_loss": sl,
                        "take_profit_1": tp1,
                        "take_profit_2": tp2,
                        "tp1_hit": False,
                        "conviction": 0.5,
                        "reasoning": "Position found on Hyperliquid (untracked locally)",
                        "opened_at": datetime.now(timezone.utc).isoformat(),
                        "current_price": mid_px,
                        "unrealized_pnl": unrealized_pnl,
                        "unrealized_pnl_pct": 0.0,
                        "remaining_size_pct": 1.0,
                    }
                    updated_positions.append(new_pos)

            # 4. Save synced positions back to local state
            self._save_local_state(updated_positions)
            return updated_positions

        except Exception as e:
            logger.error(f"Error syncing Hyperliquid positions: {e}", exc_info=True)
            # Fall back to local state if API is temporarily down
            return self._load_local_state()

    def get_portfolio_snapshot(self) -> Dict:
        """Get snapshot of live account details and open positions."""
        positions = self.positions
        unrealized = sum(p.get("unrealized_pnl", 0.0) for p in positions)
        total_equity = self.total_equity
        cash = self.cash

        wr = round((self.winning_trades / max(self.total_trades, 1)) * 100, 1)

        return {
            "cash": round(cash, 2),
            "total_equity": round(total_equity, 2),
            "unrealized_pnl": round(unrealized, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "total_fees_paid": round(self.total_fees_paid, 4),
            "deployed_pct": round(self.deployed_pct * 100, 1),
            "positions": positions,
            "open_position_count": len(positions),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": wr,
        }

    # ── Trade Execution ──────────────────────────────────────────────────────

    def _get_sz_decimals(self, coin: str) -> int:
        """Fetch position szDecimals for rounding from the asset meta."""
        try:
            meta = self.info.meta()
            for asset in meta.get("universe", []):
                if asset["name"] == coin.upper():
                    return int(asset["szDecimals"])
        except Exception as e:
            logger.error(f"Error fetching szDecimals for {coin}: {e}")
        return 4  # Sensible default fallback

    def _calculate_size(self, coin: str, size_usd: float, price: float) -> float:
        """Convert a dollar size to a correctly rounded coin size."""
        decimals = self._get_sz_decimals(coin)
        size = size_usd / price
        rounded_size = float(f"{size:.{decimals}f}")
        return rounded_size

    def open_position(
        self,
        coin: str,
        side: str,
        entry_price: float,
        size_usd: float,
        leverage: int,
        stop_loss: float,
        tp1: float,
        tp2: float,
        conviction: float = 0.5,
        reasoning: str = "",
    ) -> bool:
        """Open a new live position on Hyperliquid mainnet."""
        coin = coin.upper()

        # Check existing positions in this coin
        for pos in self.positions:
            if pos["coin"] == coin:
                logger.warning(
                    f"Already have an open live position in {coin} — skipping"
                )
                return False

        # Enforce open slots risk limit
        if len(self.positions) >= MAX_OPEN_POSITIONS:
            logger.warning(
                f"Max live positions ({MAX_OPEN_POSITIONS}) reached — skipping open"
            )
            return False

        # Set Leverage
        try:
            logger.info(f"Setting leverage for {coin} to {leverage}x...")
            self.exchange.update_leverage(leverage, coin, True)
        except Exception as e:
            logger.error(f"Failed to set leverage for {coin}: {e}")
            return False

        # Calculate correctly rounded size
        sz = self._calculate_size(coin, size_usd, entry_price)
        is_buy = side == "LONG"

        logger.info(
            f"🚀 Submitting MARKET ORDER to open {side} {coin} | Size: {sz} ({size_usd} USD)"
        )

        try:
            # Place real market open order on exchange
            result = self.exchange.market_open(
                name=coin,
                is_buy=is_buy,
                sz=sz,
                px=entry_price,  # reference mid price
                slippage=0.02,
            )

            if result.get("status") == "ok":
                logger.info(f"✅ Market order filled successfully: {result}")

                # Retrieve actual fill price if statuses is present, otherwise fallback to target entry_price
                filled_px = entry_price
                try:
                    statuses = (
                        result.get("response", {}).get("data", {}).get("statuses", [])
                    )
                    if statuses and "filled" in statuses[0]:
                        filled_px = float(
                            statuses[0]["filled"].get("avgPx", entry_price)
                        )
                        logger.info(f"Actual fill price: ${filled_px:.4f}")
                except Exception:
                    pass

                # Store tracking metadata locally
                local_pos = {
                    "coin": coin,
                    "side": side,
                    "entry_price": filled_px,
                    "size_usd": sz * filled_px,
                    "leverage": leverage,
                    "stop_loss": stop_loss,
                    "take_profit_1": tp1,
                    "take_profit_2": tp2,
                    "tp1_hit": False,
                    "conviction": conviction,
                    "reasoning": reasoning,
                    "opened_at": datetime.now(timezone.utc).isoformat(),
                    "current_price": filled_px,
                    "unrealized_pnl": 0.0,
                    "unrealized_pnl_pct": 0.0,
                    "remaining_size_pct": 1.0,
                }

                # Record entry fee + slippage locally
                entry_fee = (sz * filled_px) * HL_TAKER_FEE
                entry_slippage = (sz * filled_px) * HL_SLIPPAGE_RATE
                self.total_fees_paid += entry_fee + entry_slippage

                # Write changes to disk
                self.last_traded_token = coin.upper()
                positions = self._load_local_state()
                positions.append(local_pos)
                self._save_local_state(positions)

                # Log trade open in journal
                trade_journal.log_trade_open(
                    coin,
                    side,
                    filled_px,
                    sz * filled_px,
                    leverage,
                    stop_loss,
                    tp1,
                    tp2,
                    conviction,
                    reasoning,
                )
                return True
            else:
                logger.error(f"❌ Hyperliquid order rejected: {result}")
                return False

        except Exception as e:
            logger.error(
                f"❌ Exception occurred while opening position on Hyperliquid: {e}",
                exc_info=True,
            )
            return False

    def close_position(
        self,
        coin: str,
        exit_price: float,
        reason: str = "manual",
        close_pct: float = 1.0,
    ) -> Optional[float]:
        """Close (or partially close) a live position on Hyperliquid mainnet."""
        coin = coin.upper()

        positions = self._load_local_state()
        pos_idx = None
        for i, p in enumerate(positions):
            if p["coin"] == coin:
                pos_idx = i
                break

        if pos_idx is None:
            logger.warning(f"No tracked local position in {coin} to close")
            # Close exchange position anyway to be safe
            try:
                self.exchange.market_close(coin)
            except Exception:
                pass
            return None

        pos = positions[pos_idx]
        side = pos["side"]
        entry_price = pos["entry_price"]
        leverage = pos["leverage"]

        # Fetch actual position size from exchange
        real_sz = 0.0
        try:
            state = self.info.user_state(self.user_address)
            for entry in state.get("assetPositions", []):
                p = entry.get("position", {})
                if p.get("coin") == coin:
                    real_sz = abs(float(p.get("szi", 0)))
                    break
        except Exception:
            pass

        if real_sz == 0.0:
            logger.warning(
                f"Exchange position for {coin} is already flat. Pruning local state."
            )
            positions.pop(pos_idx)
            self._save_local_state(positions)
            return 0.0

        sz_to_close = real_sz * close_pct
        decimals = self._get_sz_decimals(coin)
        sz_to_close = float(f"{sz_to_close:.{decimals}f}")

        # If close is effectively 100% or very close, close full size
        is_full_close = close_pct >= 0.98 or (real_sz - sz_to_close) < (
            10 ** (-decimals)
        )

        logger.info(
            f"🚀 Submitting MARKET ORDER to close {coin} | Size: {sz_to_close} (Full: {is_full_close})"
        )

        try:
            # Place real market close order on exchange
            if is_full_close:
                result = self.exchange.market_close(coin=coin, slippage=0.02)
            else:
                result = self.exchange.market_close(
                    coin=coin, sz=sz_to_close, slippage=0.02
                )

            if result.get("status") == "ok":
                logger.info(f"✅ Market close order filled successfully: {result}")

                # Retrieve actual fill price
                filled_exit_px = exit_price
                try:
                    statuses = (
                        result.get("response", {}).get("data", {}).get("statuses", [])
                    )
                    if statuses and "filled" in statuses[0]:
                        filled_exit_px = float(
                            statuses[0]["filled"].get("avgPx", exit_price)
                        )
                        logger.info(f"Actual exit fill price: ${filled_exit_px:.4f}")
                except Exception:
                    pass

                # Calculate P&L
                close_size_usd = sz_to_close * filled_exit_px
                if side == "LONG":
                    pnl_pct = (filled_exit_px / entry_price - 1) * leverage * 100
                    pnl_usd = (
                        close_size_usd * (filled_exit_px / entry_price - 1)
                    )
                else:  # SHORT
                    pnl_pct = (1 - filled_exit_px / entry_price) * leverage * 100
                    pnl_usd = (
                        close_size_usd * (1 - filled_exit_px / entry_price)
                    )

                # Deduct fees
                exit_fee = close_size_usd * HL_TAKER_FEE
                exit_slippage = close_size_usd * HL_SLIPPAGE_RATE
                exit_cost = exit_fee + exit_slippage
                pnl_usd -= exit_cost
                self.total_fees_paid += exit_cost

                # Calculate hold duration
                opened_at = datetime.fromisoformat(pos["opened_at"])
                hold_hours = (
                    datetime.now(timezone.utc) - opened_at
                ).total_seconds() / 3600

                # Update stats
                self.realized_pnl += pnl_usd
                self.total_trades += 1
                if pnl_usd >= 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1

                # Log trade close in journal
                trade_journal.log_trade_close(
                    coin,
                    side,
                    entry_price,
                    filled_exit_px,
                    close_size_usd,
                    leverage,
                    pnl_usd,
                    pnl_pct,
                    reason,
                    hold_hours,
                )

                # Update local positioning list
                if is_full_close:
                    positions.pop(pos_idx)
                else:
                    positions[pos_idx]["remaining_size_pct"] *= 1 - close_pct
                    trade_journal.log_trade_update(
                        coin,
                        "PARTIAL_CLOSE",
                        f"Closed {close_pct * 100:.0f}%, remaining {positions[pos_idx]['remaining_size_pct'] * 100:.0f}%",
                    )

                self._save_local_state(positions)
                return pnl_usd
            else:
                logger.error(f"❌ Hyperliquid close order rejected: {result}")
                return None

        except Exception as e:
            logger.error(
                f"❌ Exception occurred while closing position on Hyperliquid: {e}",
                exc_info=True,
            )
            return None

    # ── Positioning Loop Checkers ───────────────────────────────────────────

    def update_prices(self, prices: dict[str, float]):
        """Keep current prices fresh. Unrealized P&L is computed dynamically."""
        self.current_prices = prices

    def check_exits(self, prices: dict[str, float]) -> List[Dict]:
        """
        Check all open live positions for SL/TP hits and max hold time.
        Returns list of exit actions taken.
        """
        actions = []
        self.current_prices = prices

        # Check copies of positions to prevent iteration race conditions
        positions_to_check = list(self.positions)

        for pos in positions_to_check:
            coin = pos["coin"]
            if coin not in prices:
                continue

            current = prices[coin]
            side = pos["side"]
            entry = pos["entry_price"]

            # Stop Loss Check
            sl_hit = False
            if side == "LONG" and current <= pos["stop_loss"]:
                sl_hit = True
            elif side == "SHORT" and current >= pos["stop_loss"]:
                sl_hit = True

            if sl_hit:
                pnl = self.close_position(coin, pos["stop_loss"], "STOP_LOSS")
                actions.append({"coin": coin, "action": "STOP_LOSS", "pnl": pnl})
                continue

            # Take Profit 1 Check (50% partial close)
            if not pos.get("tp1_hit", False):
                tp1_hit = False
                if side == "LONG" and current >= pos["take_profit_1"]:
                    tp1_hit = True
                elif side == "SHORT" and current <= pos["take_profit_1"]:
                    tp1_hit = True

                if tp1_hit:
                    pnl = self.close_position(
                        coin, pos["take_profit_1"], "TAKE_PROFIT_1", close_pct=0.5
                    )
                    # Update local state list to move stop loss to breakeven
                    positions = self._load_local_state()
                    for p in positions:
                        if p["coin"] == coin:
                            p["tp1_hit"] = True
                            p["stop_loss"] = entry
                            trade_journal.log_trade_update(
                                coin,
                                "MOVE_SL_BREAKEVEN",
                                f"TP1 hit. SL moved to breakeven ${entry:.4f}",
                            )
                            break
                    self._save_local_state(positions)
                    actions.append(
                        {"coin": coin, "action": "TP1_PARTIAL_CLOSE", "pnl": pnl}
                    )
                    continue

            # Take Profit 2 Check (close remaining)
            tp2_hit = False
            if side == "LONG" and current >= pos["take_profit_2"]:
                tp2_hit = True
            elif side == "SHORT" and current <= pos["take_profit_2"]:
                tp2_hit = True

            if tp2_hit:
                pnl = self.close_position(coin, pos["take_profit_2"], "TAKE_PROFIT_2")
                actions.append({"coin": coin, "action": "TP2_FULL_CLOSE", "pnl": pnl})
                continue

            # ROE Exit Check
            roe = pos.get("unrealized_pnl_pct", 0)
            if roe >= MIN_ROE_EXIT_PCT:
                pnl = self.close_position(
                    coin, current, f"ROE_EXIT_{MIN_ROE_EXIT_PCT}%"
                )
                actions.append({"coin": coin, "action": "ROE_EXIT", "pnl": pnl})
                continue

            # Max Hold Expiry Check
            opened_at = datetime.fromisoformat(pos["opened_at"])
            hold_hours = (datetime.now(timezone.utc) - opened_at).total_seconds() / 3600
            if hold_hours >= MAX_HOLD_HOURS:
                pnl = self.close_position(coin, current, f"MAX_HOLD_{MAX_HOLD_HOURS}H")
                actions.append({"coin": coin, "action": "MAX_HOLD_EXPIRED", "pnl": pnl})
                continue

        return actions

    # ── AI-Driven Stop Updates ───────────────────────────────────────────────

    def apply_ai_updates(self, updates: List[Dict], prices: dict[str, float]):
        """Apply stop moves or closures decided by Claude AI."""
        self.current_prices = prices

        for update in updates:
            coin = update.get("coin", "").upper()
            action = update.get("action", "")
            reasoning = update.get("reasoning", "")

            positions = self._load_local_state()
            pos = None
            for p in positions:
                if p["coin"] == coin:
                    pos = p
                    break

            if pos is None:
                logger.warning(f"AI update for {coin} but no tracked open position")
                continue

            if action == "MOVE_STOP_TO_BREAKEVEN":
                positions = self._load_local_state()
                for p in positions:
                    if p["coin"] == coin:
                        p["stop_loss"] = p["entry_price"]
                        break
                self._save_local_state(positions)
                trade_journal.log_trade_update(coin, action, reasoning)

            elif action == "TIGHTEN_STOP":
                new_sl = update.get("new_stop_loss")
                if new_sl:
                    positions = self._load_local_state()
                    for p in positions:
                        if p["coin"] == coin:
                            p["stop_loss"] = new_sl
                            break
                    self._save_local_state(positions)
                    trade_journal.log_trade_update(
                        coin, action, f"SL → ${new_sl:.4f}. {reasoning}"
                    )

            elif action == "CLOSE":
                exit_price = float(prices.get(coin) or pos.get("current_price", 0.0))
                self.close_position(coin, exit_price, f"AI_CLOSE: {reasoning}")

            elif action == "PARTIAL_CLOSE":
                exit_price = float(prices.get(coin) or pos.get("current_price", 0.0))
                pct = update.get("close_pct", 0.5)
                self.close_position(
                    coin, exit_price, f"AI_PARTIAL: {reasoning}", close_pct=pct
                )
