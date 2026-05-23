# file: strategies_lib/candle_2_closure_luxalgo.py
import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class Candle2ClosureStrategy:
    """Candle 2 Closure [LuxAlgo]"""

    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 use_filter=False, filter_length=20, wick_threshold_pct=40,
                 use_candle2=True, use_candle3=True, min_bars_between=5,
                 max_hold_bars=0, take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.use_filter        = use_filter
        self.filter_len        = filter_length
        self.wick_pct          = wick_threshold_pct / 100.0
        self.use_c2            = use_candle2
        self.use_c3            = use_candle3
        self.min_bars_between  = min_bars_between
        self.max_hold          = max_hold_bars
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < self.filter_len + 1:
            return {"error": f"Not enough data (need >= {self.filter_len + 1} bars)",
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

        # Signals
        df["bull_rev"] = (df["close"].shift(1) < df["open"].shift(1)) & (df["low"] < df["low"].shift(1)) & (df["close"] > df["low"].shift(1))
        df["bear_rev"] = (df["close"].shift(1) > df["open"].shift(1)) & (df["high"] > df["high"].shift(1)) & (df["close"] < df["high"].shift(1))
        if self.use_filter:
            df["bull_rev"] &= df["low"]  == df["low"].rolling(self.filter_len).min()
            df["bear_rev"] &= df["high"] == df["high"].rolling(self.filter_len).max()
        df["bull_exp"] = df["bull_rev"].shift(1) & (df["low"] > df["low"].shift(1)) & (df["close"] > df["high"].shift(1))
        df["bear_exp"] = df["bear_rev"].shift(1) & (df["high"] < df["high"].shift(1)) & (df["close"] < df["low"].shift(1))
        df["bull_sig"] = (self.use_c2 & df["bull_rev"]) | (self.use_c3 & df["bull_exp"])
        df["bear_sig"] = (self.use_c2 & df["bear_rev"]) | (self.use_c3 & df["bear_exp"])

        equity = [self.initial_capital]
        position = 0; entry_price = 0.0; entry_time = None
        last_signal_idx = -9999
        trades: list = []

        for i in range(1, len(df)):
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

            gap       = i - last_signal_idx >= self.min_bars_between
            long_sig  = bool(row["bull_sig"]) and gap
            short_sig = bool(row["bear_sig"]) and gap

            if long_sig and position <= 0:
                if position == -1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position = 1; entry_price = row["close"]; entry_time = dt; last_signal_idx = i
            elif short_sig and position >= 0:
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