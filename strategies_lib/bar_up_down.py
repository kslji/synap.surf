# file: strategies_lib/bar_up_down.py
"""
BarUpDn reversal strategy — REFACTORED
All 5 common bugs fixed via base_strategy helpers.
"""

import pandas as pd
from typing import Dict, Any

from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class BarUpDnStrategy:
    """
    BarUpDn reversal (always in market, flips on signal)

    Signals:
      Long  : close > open  AND  open > close[1]
      Short : close < open  AND  open < close[1]

    Exits:
      - Stop loss  (SL)   — structure-aware, pessimistic same-bar resolution
      - Take profit (TP)
      - Signal flip       — always reverses on opposite signal (BUG 2 fixed)
    """

    def __init__(
        self,
        initial_capital:       float = 1000.0,
        position_size_pct:     float = 1.0,
        max_intraday_loss_pct: float = 1.0,   # kept for API compat
        take_profit_pct:       float = 2.0,
        sl_pct:                float = 1.0,
    ):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < 2:
            return {"error": "Not enough data (minimum 2 bars)"}

        required = ["open", "high", "low", "close", "open_time_utc"]
        missing  = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])

        equity      = [self.initial_capital]
        position    = 0
        entry_price = 0.0
        entry_time  = None
        trades: list = []

        for i in range(1, len(df)):
            row  = df.iloc[i]
            prev = df.iloc[i - 1]
            dt   = row["open_time_utc"]          # BUG 4 — assign once
            eq   = equity[-1]                    # BUG 3 — local copy

            # ── TP / SL (BUG 5 — pessimistic same-bar) ───────────────────────
            if position != 0:
                sl = entry_price * (1 - self.sl_pct) if position == 1 \
                     else entry_price * (1 + self.sl_pct)
                tp = entry_price * (1 + self.take_profit_pct / 100) if position == 1 \
                     else entry_price * (1 - self.take_profit_pct / 100)

                hit = resolve_exit(row, position, sl, tp)

                if hit == "sl":
                    eq, position, entry_price, entry_time = close_trade(
                        trades, eq, position, entry_price,
                        entry_time, sl, dt,
                        self.position_size_pct, "sl_hit",
                    )
                    equity.append(eq)
                    continue

                if hit == "tp":
                    eq, position, entry_price, entry_time = close_trade(
                        trades, eq, position, entry_price,
                        entry_time, tp, dt,
                        self.position_size_pct, "take_profit",
                    )
                    # fall through — allow new entry on same bar after TP

            # ── Signals ───────────────────────────────────────────────────────
            bull = (row["close"] > row["open"]) and (row["open"] > prev["close"])
            bear = (row["close"] < row["open"]) and (row["open"] < prev["close"])

            if bull and position <= 0:
                if position == -1:              # BUG 2 — unconditional close
                    eq, position, entry_price, entry_time = close_trade(
                        trades, eq, position, entry_price,
                        entry_time, row["close"], dt,
                        self.position_size_pct, "signal_flip",
                    )
                position    = 1
                entry_price = row["close"]
                entry_time  = dt

            elif bear and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(
                        trades, eq, position, entry_price,
                        entry_time, row["close"], dt,
                        self.position_size_pct, "signal_flip",
                    )
                position    = -1
                entry_price = row["close"]
                entry_time  = dt

            equity.append(eq)                   # BUG 3 — append once per bar

        # ── Close open position ───────────────────────────────────────────────
        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(
                trades, equity[-1], position, entry_price,
                entry_time, last["close"], last["open_time_utc"],
                self.position_size_pct, "end_of_data",
            )
            equity[-1] = eq

        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results