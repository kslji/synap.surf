# file: strategies_lib/inside_bar_strategy.py
import pandas as pd
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class InsideBarStrategy:
    """Inside Bar reversal — all 5 bugs fixed."""

    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 max_intraday_loss_pct=1.0, take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0

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
            dt   = row["open_time_utc"]
            eq   = equity[-1]

            if position != 0:
                sl  = entry_price * (1 - self.sl_pct) if position == 1 else entry_price * (1 + self.sl_pct)
                tp  = entry_price * (1 + self.take_profit_pct / 100) if position == 1 else entry_price * (1 - self.take_profit_pct / 100)
                hit = resolve_exit(row, position, sl, tp)
                if hit == "sl":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, sl, dt, self.position_size_pct, "sl_hit")
                    equity.append(eq); continue
                if hit == "tp":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, tp, dt, self.position_size_pct, "take_profit")

            is_inside = (row["high"] < prev["high"]) and (row["low"] > prev["low"])
            if not is_inside:
                equity.append(eq); continue

            if (row["close"] > row["open"]) and position <= 0:
                if position == -1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position = 1; entry_price = row["close"]; entry_time = dt

            elif (row["close"] < row["open"]) and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position = -1; entry_price = row["close"]; entry_time = dt

            equity.append(eq)

        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last["open_time_utc"], self.position_size_pct, "end_of_data")
            equity[-1] = eq

        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results