# file: strategies_lib/bollinger_bands.py
"""
Bollinger Bands mean-reversion strategy — REFACTORED
All 5 common bugs fixed via base_strategy helpers.
"""

import pandas as pd
from typing import Dict, Any

from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class BollingerStrategy:
    """
    Bollinger Bands mean-reversion (classic version)

    Signals:
      Long  : close crosses above lower band (prev close <= lower, curr close > lower)
      Short : close crosses below upper band (prev close >= upper, curr close < upper)

    Exits:
      - Stop loss / Take profit with pessimistic same-bar resolution
      - Opposite signal close (unconditional — BUG 2 fixed)
    """

    def __init__(
        self,
        initial_capital:       float = 1000.0,
        position_size_pct:     float = 1.0,
        bb_length:             int   = 50,
        bb_mult:               float = 2.1,
        max_intraday_loss_pct: float = 1.0,   # kept for API compat
        take_profit_pct:       float = 2.0,
        sl_pct:                float = 1.0,
    ):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.bb_length         = bb_length
        self.bb_mult           = bb_mult
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < self.bb_length + 1:
            return {"error": f"Not enough data (need ≥ {self.bb_length + 1} bars)"}

        required = ["open", "high", "low", "close", "open_time_utc"]
        missing  = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])

        # Bollinger Bands
        roll      = df["close"].rolling(self.bb_length)
        df["mid"] = roll.mean()
        df["std"] = roll.std()
        df["upper"] = df["mid"] + self.bb_mult * df["std"]
        df["lower"] = df["mid"] - self.bb_mult * df["std"]

        equity      = [self.initial_capital]
        position    = 0
        entry_price = 0.0
        entry_time  = None
        trades: list = []

        for i in range(self.bb_length, len(df)):
            row  = df.iloc[i]
            prev = df.iloc[i - 1]
            dt   = row["open_time_utc"]          # BUG 4
            eq   = equity[-1]

            # ── TP / SL (BUG 5) ──────────────────────────────────────────────
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

            # ── Signals ───────────────────────────────────────────────────────
            long_sig  = (prev["close"] <= prev["lower"]) and (row["close"] > row["lower"])
            short_sig = (prev["close"] >= prev["upper"]) and (row["close"] < row["upper"])

            if long_sig and position <= 0:
                if position == -1:              # BUG 2
                    eq, position, entry_price, entry_time = close_trade(
                        trades, eq, position, entry_price,
                        entry_time, row["close"], dt,
                        self.position_size_pct, "opposite_signal",
                    )
                position    = 1
                entry_price = row["close"]
                entry_time  = dt

            elif short_sig and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(
                        trades, eq, position, entry_price,
                        entry_time, row["close"], dt,
                        self.position_size_pct, "opposite_signal",
                    )
                position    = -1
                entry_price = row["close"]
                entry_time  = dt

            equity.append(eq)                   # BUG 3

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