# file: strategies_lib/fibonacci_sequence_grid_bigbeluga.py
import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class FibonacciSequenceGridStrategy:
    """Fibonacci Sequence Grid [BigBeluga] — all 5 bugs fixed."""

    FIB = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]

    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 lookback_length=100, angle=4.0, max_grids=10,
                 use_trend_filter=True, min_bars_between=5,
                 max_hold_bars=0, take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.lookback          = lookback_length
        self.angle             = angle
        self.max_grids         = max_grids
        self.use_trend         = use_trend_filter
        self.min_bars_between  = min_bars_between
        self.max_hold          = max_hold_bars
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        min_bars = self.lookback * 2
        if len(df) < min_bars:
            return {"error": f"Not enough data (need >= {min_bars} bars)",
                    "final_equity": self.initial_capital, "total_return_%": 0.0,
                    "max_drawdown_%": 0.0, "n_trades": 0, "win_rate_%": 0.0,
                    "trade_log": pd.DataFrame(), "equity_curve": pd.Series([self.initial_capital])}

        required = ["open", "high", "low", "close"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        df = df.copy().reset_index(drop=True)
        tc = "open_time_utc" if "open_time_utc" in df.columns else "timestamp"
        if tc in df.columns:
            df[tc] = pd.to_datetime(df[tc])

        w = 2 * self.lookback + 1
        df["high_swing"] = df["high"].rolling(w, center=True).max() == df["high"]
        df["low_swing"]  = df["low"].rolling(w, center=True).min()  == df["low"]
        df["ema_fast"]   = df["close"].ewm(span=12, adjust=False).mean()
        df["ema_slow"]   = df["close"].ewm(span=26, adjust=False).mean()
        df["trend"]      = np.where(df["ema_fast"] > df["ema_slow"], 1, -1)

        equity = [self.initial_capital]
        position = 0; entry_price = 0.0; entry_time = None
        last_signal_idx = -9999; grids = []
        trades: list = []

        for i in range(min_bars, len(df)):
            row = df.iloc[i]
            dt  = row.get(tc)
            eq  = equity[-1]

            if position != 0:
                sl  = entry_price * (1 - self.sl_pct) if position == 1 else entry_price * (1 + self.sl_pct)
                tp  = entry_price * (1 + self.take_profit_pct / 100) if position == 1 else entry_price * (1 - self.take_profit_pct / 100)
                hit = resolve_exit(row, position, sl, tp)
                if hit == "sl":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, sl, dt, self.position_size_pct, "sl_hit")
                    equity.append(eq); continue
                if hit == "tp":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, tp, dt, self.position_size_pct, "take_profit")

            if self.max_hold > 0 and position != 0 and (i - last_signal_idx) >= self.max_hold:
                eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "time_exit")

            ws = max(0, i - self.lookback); win = df.iloc[ws: i + 1]
            if bool(row["high_swing"]) or bool(row["low_swing"]):
                gmax = win["high"].max(); gmin = win["low"].min()
                step = (gmax - gmin) / max(self.angle, 1e-9)
                anchor = gmax if bool(row["high_swing"]) else gmin
                grids.append({"upper": [anchor + step * f for f in self.FIB], "lower": [anchor - step * f for f in self.FIB]})
            grids = grids[-self.max_grids:]

            prev_close = df.iloc[i - 1]["close"]
            long_sig = any(prev_close < lvl <= row["close"] for g in grids for lvl in g["lower"])
            short_sig = any(prev_close > lvl >= row["close"] for g in grids for lvl in g["upper"])
            if self.use_trend:
                long_sig  = long_sig  and row["trend"] > 0
                short_sig = short_sig and row["trend"] < 0
            gap = i - last_signal_idx >= self.min_bars_between

            if long_sig and gap and position <= 0:
                if position == -1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position = 1; entry_price = row["close"]; entry_time = dt; last_signal_idx = i
            elif short_sig and gap and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position = -1; entry_price = row["close"]; entry_time = dt; last_signal_idx = i

            equity.append(eq)

        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last.get(tc), self.position_size_pct, "end_of_data")
            equity[-1] = eq

        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results