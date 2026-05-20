# file: strategies_lib/greedy.py
import pandas as pd
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class GreedyStrategy:
    """Gap-based Greedy strategy — all 5 bugs fixed."""

    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 tp_ticks=10, sl_ticks=10, tick_size=0.01,
                 max_intraday_loss_pct=1.0, take_profit_pct=2.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.tp_ticks          = tp_ticks
        self.sl_ticks          = sl_ticks
        self.tick_size         = tick_size
        self.take_profit_pct   = take_profit_pct
        # sl_pct derived from tick-based SL for resolve_exit compatibility
        self.sl_pct            = (sl_ticks * tick_size) / 100.0

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < 2:
            return {"error": "Not enough data"}

        required = ["open", "high", "low", "close", "open_time_utc"]
        missing  = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

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
            dt   = row["open_time_utc"]              # BUG 4
            eq   = equity[-1]                        # BUG 3

            # ── TP / SL — tick-based levels (BUG 5) ──────────────────────────
            if position != 0:
                dir_sign = 1 if position == 1 else -1
                sl = entry_price - dir_sign * self.sl_ticks * self.tick_size
                tp = entry_price + dir_sign * self.tp_ticks * self.tick_size
                hit = resolve_exit(row, position, sl, tp)
                if hit == "sl":
                    eq, position, entry_price, entry_time = close_trade(
                        trades, eq, position, entry_price, entry_time,
                        sl, dt, self.position_size_pct, "stop_loss")
                    equity.append(eq); continue
                if hit == "tp":
                    eq, position, entry_price, entry_time = close_trade(
                        trades, eq, position, entry_price, entry_time,
                        tp, dt, self.position_size_pct, "take_profit")

            # ── Gap signals ───────────────────────────────────────────────────
            gap_up   = row["open"] > prev["high"]
            gap_down = row["open"] < prev["low"]

            if gap_up and position <= 0:
                ep = prev["high"]
                if row["high"] >= ep:
                    if position == -1:               # BUG 2
                        eq, position, entry_price, entry_time = close_trade(
                            trades, eq, position, entry_price, entry_time,
                            max(row["open"], ep), dt,
                            self.position_size_pct, "gap_reverse")
                    position    = 1
                    entry_price = max(row["open"], ep)
                    entry_time  = dt

            elif gap_down and position >= 0:
                ep = prev["low"]
                if row["low"] <= ep:
                    if position == 1:
                        eq, position, entry_price, entry_time = close_trade(
                            trades, eq, position, entry_price, entry_time,
                            min(row["open"], ep), dt,
                            self.position_size_pct, "gap_reverse")
                    position    = -1
                    entry_price = min(row["open"], ep)
                    entry_time  = dt

            equity.append(eq)                        # BUG 3

        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price,
                entry_time, last["close"], last["open_time_utc"],
                self.position_size_pct, "end_of_data")
            equity[-1] = eq

        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results