#!/usr/bin/env python3
"""
brain/paper_trader.py — Paper trading engine + position manager.

Tracks:
  - Open positions with full metadata (entry, SL, TP, leverage)
  - Unrealized P&L (mark-to-market each cycle)
  - Closed trades with realized P&L
  - Portfolio state: cash, equity, margin

Persists state to JSON so it survives restarts.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from algo_brain.config import (
    INITIAL_CAPITAL,
    MAX_OPEN_POSITIONS,
    MAX_CAPITAL_PER_TRADE_PCT,
    MAX_TOTAL_DEPLOYED_PCT,
    MAX_HOLD_HOURS,
    HL_FEE_RATE,
    HL_SLIPPAGE_RATE,
    MIN_ROE_EXIT_PCT,
)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from backend.db import get_db
from algo_brain import trade_journal

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# POSITION DATA STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════


def _new_position(
    coin: str,
    side: str,
    entry_price: float,
    size_usd: float,
    leverage: int,
    stop_loss: float,
    tp1: float,
    tp2: float,
    conviction: float,
    reasoning: str,
) -> dict:
    return {
        "coin": coin,
        "side": side,  # "LONG" or "SHORT"
        "entry_price": entry_price,
        "size_usd": size_usd,  # Notional value
        "leverage": leverage,
        "stop_loss": stop_loss,
        "take_profit_1": tp1,
        "take_profit_2": tp2,
        "tp1_hit": False,  # Track partial closes
        "conviction": conviction,
        "reasoning": reasoning,
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "current_price": entry_price,
        "unrealized_pnl": 0.0,
        "unrealized_pnl_pct": 0.0,
        "remaining_size_pct": 1.0,  # 1.0 = full, 0.5 = half closed at TP1
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADER
# ═══════════════════════════════════════════════════════════════════════════════


class PaperTrader:
    """
    Paper trading engine. Simulates fills at signal price.
    Tracks P&L, enforces risk limits, persists state.
    """

    def __init__(self):
        self.cash: float = INITIAL_CAPITAL
        self.positions: list[dict] = []
        self.closed_trades: list[dict] = []
        self.realized_pnl: float = 0.0
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.total_fees_paid: float = 0.0  # Cumulative HL fees + slippage
        self.last_traded_token: str = ""
        self._load_state()

    # ── State Persistence ────────────────────────────────────────────────────

    def _load_state(self):
        """Load portfolio state from database."""
        try:
            with get_db() as db:
                row = db.execute("SELECT * FROM portfolios WHERE user_id = 'PAPER_USER' AND portfolio_type = 'PAPER'").fetchone()
                if row:
                    self.cash = row["cash"]
                    self.realized_pnl = row["realized_pnl"]
                    self.total_trades = row["total_trades"]
                    self.winning_trades = row["winning_trades"]
                    self.losing_trades = row["losing_trades"]
                    
                    # We also load the raw JSON positions state to preserve all metadata easily
                    kv_row = db.execute("SELECT value_json FROM market_data WHERE key = 'paper_positions'").fetchone()
                    if kv_row:
                        self.positions = json.loads(kv_row["value_json"])
                    
                    logger.info(
                        f"📂 Loaded portfolio: cash=${self.cash:.2f}, "
                        f"{len(self.positions)} open positions, "
                        f"realized P&L=${self.realized_pnl:+.2f}"
                    )
        except Exception as e:
            logger.warning(f"Could not load portfolio state: {e}. Starting fresh.")

    def _save_state(self):
        """Save portfolio state to database."""
        try:
            with get_db() as db:
                db.execute('''
                    INSERT INTO portfolios (user_id, portfolio_type, cash, total_equity, unrealized_pnl, realized_pnl, total_trades, winning_trades, losing_trades)
                    VALUES ('PAPER_USER', 'PAPER', ?, ?, ?, ?, ?, ?, ?)
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
                    round(self.cash, 2),
                    round(self.total_equity, 2),
                    round(sum(p.get("unrealized_pnl", 0) for p in self.positions), 2),
                    round(self.realized_pnl, 2),
                    self.total_trades,
                    self.winning_trades,
                    self.losing_trades
                ))
                
                # Save raw positions to kv_store to preserve full memory metadata easily
                db.execute('''
                    INSERT INTO market_data (key, value_json) VALUES ('paper_positions', ?)
                    ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=CURRENT_TIMESTAMP
                ''', (json.dumps(self.positions, default=str),))
                
        except Exception as e:
            logger.error(f"Failed to save portfolio state: {e}")

    # ── Portfolio Info ────────────────────────────────────────────────────────

    @property
    def total_equity(self) -> float:
        """Cash + unrealized P&L."""
        unrealized = sum(p.get("unrealized_pnl", 0) for p in self.positions)
        return self.cash + unrealized

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

    def get_portfolio_snapshot(self) -> dict:
        """Get full portfolio state for logging and AI input."""
        unrealized = sum(p.get("unrealized_pnl", 0) for p in self.positions)
        return {
            "cash": round(self.cash, 2),
            "total_equity": round(self.total_equity, 2),
            "unrealized_pnl": round(unrealized, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "total_fees_paid": round(self.total_fees_paid, 4),
            "deployed_pct": round(self.deployed_pct * 100, 1),
            "positions": self.positions,
            "open_position_count": len(self.positions),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.winning_trades / max(self.total_trades, 1) * 100, 1),
        }

    # ── Trade Execution ──────────────────────────────────────────────────────

    def can_open_trade(self, size_usd: float, leverage: int) -> tuple[bool, str]:
        """Check if a new trade can be opened within risk limits."""
        if len(self.positions) >= MAX_OPEN_POSITIONS:
            return False, f"Max positions ({MAX_OPEN_POSITIONS}) reached"

        margin_needed = size_usd / leverage
        max_per_trade = self.total_equity * MAX_CAPITAL_PER_TRADE_PCT
        if margin_needed > max_per_trade:
            return (
                False,
                f"Margin ${margin_needed:.2f} exceeds max ${max_per_trade:.2f}",
            )

        new_deployed = self.total_deployed + margin_needed
        max_deployed = self.total_equity * MAX_TOTAL_DEPLOYED_PCT
        if new_deployed > max_deployed:
            return (
                False,
                f"Total deployed ${new_deployed:.2f} would exceed max ${max_deployed:.2f}",
            )

        if margin_needed > self.cash:
            return (
                False,
                f"Insufficient cash (${self.cash:.2f}) for margin (${margin_needed:.2f})",
            )

        return True, "OK"

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
        """Open a new paper trade position."""
        # Check for existing position in same coin
        for pos in self.positions:
            if pos["coin"] == coin:
                logger.warning(f"Already have an open position in {coin} — skipping")
                return False

        can_open, reason = self.can_open_trade(size_usd, leverage)
        if not can_open:
            logger.warning(f"Cannot open {side} {coin}: {reason}")
            return False

        # ── Entry cost: taker fee + slippage (both on notional) ──────────
        entry_fee = size_usd * HL_FEE_RATE
        entry_slippage = size_usd * HL_SLIPPAGE_RATE
        entry_cost = entry_fee + entry_slippage
        self.total_fees_paid += entry_cost

        pos = _new_position(
            coin,
            side,
            entry_price,
            size_usd,
            leverage,
            stop_loss,
            tp1,
            tp2,
            conviction,
            reasoning,
        )
        self.positions.append(pos)
        self.last_traded_token = coin.upper()

        # Reserve margin + entry cost from cash
        margin = size_usd / leverage
        self.cash -= margin + entry_cost

        logger.info(
            f"  💸 Entry cost for {coin}: fee=${entry_fee:.2f} + "
            f"slippage=${entry_slippage:.2f} = ${entry_cost:.2f} "
            f"(total fees paid: ${self.total_fees_paid:.2f})"
        )

        # Log
        trade_journal.log_trade_open(
            coin,
            side,
            entry_price,
            size_usd,
            leverage,
            stop_loss,
            tp1,
            tp2,
            conviction,
            reasoning,
        )

        self._save_state()
        return True

    def close_position(
        self,
        coin: str,
        exit_price: float,
        reason: str = "manual",
        close_pct: float = 1.0,  # 1.0 = full close, 0.5 = half
    ) -> Optional[float]:
        """
        Close (or partially close) a position.
        Returns realized P&L for the closed portion, or None if not found.
        """
        pos_idx = None
        for i, pos in enumerate(self.positions):
            if pos["coin"] == coin:
                pos_idx = i
                break

        if pos_idx is None:
            logger.warning(f"No open position in {coin} to close")
            return None

        pos = self.positions[pos_idx]
        side = pos["side"]
        entry_price = pos["entry_price"]
        full_size = pos["size_usd"]
        leverage = pos["leverage"]
        remaining = pos["remaining_size_pct"]

        # Calculate raw P&L for the portion being closed
        close_size = full_size * remaining * close_pct
        if side == "LONG":
            pnl_pct = (exit_price / entry_price - 1) * leverage * 100
            pnl_usd = close_size * (exit_price / entry_price - 1)
        else:  # SHORT
            pnl_pct = (1 - exit_price / entry_price) * leverage * 100
            pnl_usd = close_size * (1 - exit_price / entry_price)

        # ── Exit cost: taker fee + slippage on close notional ────────────
        exit_fee = close_size * HL_FEE_RATE
        exit_slippage = close_size * HL_SLIPPAGE_RATE
        exit_cost = exit_fee + exit_slippage
        pnl_usd -= exit_cost
        self.total_fees_paid += exit_cost
        logger.info(
            f"  💸 Exit cost for {coin}: fee=${exit_fee:.2f} + "
            f"slippage=${exit_slippage:.2f} = ${exit_cost:.2f} "
            f"| net P&L after costs: ${pnl_usd:+.2f}"
        )

        # Calculate hold duration
        opened_at = datetime.fromisoformat(pos["opened_at"])
        hold_hours = (datetime.now(timezone.utc) - opened_at).total_seconds() / 3600

        # Return margin + P&L to cash
        margin_returned = close_size / leverage
        self.cash += margin_returned + pnl_usd

        # Update stats
        self.realized_pnl += pnl_usd
        self.total_trades += 1
        if pnl_usd >= 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        # Log the close
        trade_journal.log_trade_close(
            coin,
            side,
            entry_price,
            exit_price,
            close_size,
            leverage,
            pnl_usd,
            pnl_pct,
            reason,
            hold_hours,
        )

        if close_pct >= 1.0 or pos["remaining_size_pct"] * (1 - close_pct) < 0.01:
            # Full close
            self.positions.pop(pos_idx)
        else:
            # Partial close
            pos["remaining_size_pct"] *= 1 - close_pct
            trade_journal.log_trade_update(
                coin,
                "PARTIAL_CLOSE",
                f"Closed {close_pct * 100:.0f}%, remaining {pos['remaining_size_pct'] * 100:.0f}%",
            )

        self._save_state()
        return pnl_usd

    # ── Mark-to-Market ───────────────────────────────────────────────────────

    def update_prices(self, prices: dict[str, float]):
        """
        Update current prices for all open positions.
        Recalculates unrealized P&L.
        """
        for pos in self.positions:
            coin = pos["coin"]
            if coin in prices:
                current = prices[coin]
                pos["current_price"] = current
                side = pos["side"]
                entry = pos["entry_price"]
                lev = pos["leverage"]
                size = pos["size_usd"] * pos["remaining_size_pct"]

                if side == "LONG":
                    pos["unrealized_pnl"] = size * (current / entry - 1)
                    pos["unrealized_pnl_pct"] = (current / entry - 1) * lev * 100
                else:
                    pos["unrealized_pnl"] = size * (1 - current / entry)
                    pos["unrealized_pnl_pct"] = (1 - current / entry) * lev * 100

        self._save_state()

    # ── SL / TP / Expiry Checks ──────────────────────────────────────────────

    def check_exits(self, prices: dict[str, float]) -> list[dict]:
        """
        Check all open positions for SL/TP hits and max hold time.
        Returns list of actions taken.
        """
        actions = []
        # Work on a copy of positions list since we may modify it
        positions_to_check = list(self.positions)

        for pos in positions_to_check:
            coin = pos["coin"]
            if coin not in prices:
                continue

            current = prices[coin]
            side = pos["side"]
            entry = pos["entry_price"]

            # ── Stop Loss ────────────────────────────────────────────
            sl_hit = False
            if side == "LONG" and current <= pos["stop_loss"]:
                sl_hit = True
            elif side == "SHORT" and current >= pos["stop_loss"]:
                sl_hit = True

            if sl_hit:
                pnl = self.close_position(coin, pos["stop_loss"], "STOP_LOSS")
                actions.append({"coin": coin, "action": "STOP_LOSS", "pnl": pnl})
                continue

            # ── Take Profit 1 (close 50%) ────────────────────────────
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
                    # Update remaining position's SL to breakeven
                    for p in self.positions:
                        if p["coin"] == coin:
                            p["tp1_hit"] = True
                            p["stop_loss"] = entry  # Move SL to breakeven
                            trade_journal.log_trade_update(
                                coin,
                                "MOVE_SL_BREAKEVEN",
                                f"TP1 hit. SL moved to breakeven ${entry:.4f}",
                            )
                            break
                    actions.append(
                        {"coin": coin, "action": "TP1_PARTIAL_CLOSE", "pnl": pnl}
                    )
                    continue

            # ── Take Profit 2 (close remaining) ──────────────────────
            tp2_hit = False
            if side == "LONG" and current >= pos["take_profit_2"]:
                tp2_hit = True
            elif side == "SHORT" and current <= pos["take_profit_2"]:
                tp2_hit = True

            if tp2_hit:
                pnl = self.close_position(coin, pos["take_profit_2"], "TAKE_PROFIT_2")
                actions.append({"coin": coin, "action": "TP2_FULL_CLOSE", "pnl": pnl})
                continue


            # ── ROE Exit Check ───────────────────────────────────────
            roe = pos.get("unrealized_pnl_pct", 0)
            if roe >= MIN_ROE_EXIT_PCT:
                pnl = self.close_position(
                    coin, current, f"ROE_EXIT_{MIN_ROE_EXIT_PCT}%"
                )
                actions.append({"coin": coin, "action": "ROE_EXIT", "pnl": pnl})
                continue

            # ── Max hold time ────────────────────────────────────────
            opened_at = datetime.fromisoformat(pos["opened_at"])
            hold_hours = (datetime.now(timezone.utc) - opened_at).total_seconds() / 3600
            if hold_hours >= MAX_HOLD_HOURS:
                pnl = self.close_position(coin, current, f"MAX_HOLD_{MAX_HOLD_HOURS}H")
                actions.append({"coin": coin, "action": "MAX_HOLD_EXPIRED", "pnl": pnl})
                continue

        return actions

    # ── AI-Driven Position Updates ───────────────────────────────────────────

    def apply_ai_updates(self, updates: list[dict], prices: dict[str, float]):
        """
        Apply position updates from Claude's decision.
        Supports: MOVE_STOP_TO_BREAKEVEN, TIGHTEN_STOP, CLOSE, ADD_TO_POSITION
        """
        for update in updates:
            coin = update.get("coin", "")
            action = update.get("action", "")
            reasoning = update.get("reasoning", "")

            pos = None
            for p in self.positions:
                if p["coin"] == coin:
                    pos = p
                    break

            if pos is None:
                logger.warning(f"AI update for {coin} but no open position")
                continue

            if action == "MOVE_STOP_TO_BREAKEVEN":
                pos["stop_loss"] = pos["entry_price"]
                trade_journal.log_trade_update(coin, action, reasoning)

            elif action == "TIGHTEN_STOP":
                new_sl = update.get("new_stop_loss")
                if new_sl:
                    pos["stop_loss"] = new_sl
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

            else:
                logger.warning(f"Unknown AI action: {action} for {coin}")
