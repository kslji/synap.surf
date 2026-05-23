# file: strategies/volty_expan_close.py

import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class VoltyExpanCloseStrategy:
    """Volty Expan Close stop-order strategy"""
 
    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 vol_length=5, vol_multiplier=0.75,
                 max_intraday_loss_pct=1.0, take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.vol_length        = vol_length
        self.vol_multiplier    = vol_multiplier
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0
 
    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < self.vol_length + 1:
            return {"error": f"Not enough data (need ≥ {self.vol_length + 1} bars)"}
        required = ["open", "high", "low", "close", "open_time_utc"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
 
        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])
 
        tr = pd.concat([df["high"]-df["low"],
                        (df["high"]-df["close"].shift(1)).abs(),
                        (df["low"] -df["close"].shift(1)).abs()], axis=1).max(axis=1)
        atrs = tr.rolling(self.vol_length).mean() * self.vol_multiplier
        df["upper_stop"] = df["close"] + atrs
        df["lower_stop"] = df["close"] - atrs
 
        equity = [self.initial_capital]; position = 0; entry_price = 0.0; entry_time = None
        trades: list = []
 
        for i in range(self.vol_length + 1, len(df)):
            row = df.iloc[i]; dt = row["open_time_utc"]; eq = equity[-1]
 
            if position != 0:
                sl = entry_price*(1-self.sl_pct) if position==1 else entry_price*(1+self.sl_pct)
                tp = entry_price*(1+self.take_profit_pct/100) if position==1 else entry_price*(1-self.take_profit_pct/100)
                hit = resolve_exit(row, position, sl, tp)
                if hit == "sl":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, sl, dt, self.position_size_pct, "sl_hit")
                    equity.append(eq); continue
                if hit == "tp":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, tp, dt, self.position_size_pct, "take_profit")
 
            if row["high"] >= row["upper_stop"] and position <= 0:
                if position == -1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["upper_stop"], dt, self.position_size_pct, "opposite_trigger")
                position = 1; entry_price = max(row["open"], row["upper_stop"]); entry_time = dt
            elif row["low"] <= row["lower_stop"] and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["lower_stop"], dt, self.position_size_pct, "opposite_trigger")
                position = -1; entry_price = min(row["open"], row["lower_stop"]); entry_time = dt
 
            equity.append(eq)
 
        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last["open_time_utc"], self.position_size_pct, "end_of_data")
            equity[-1] = eq
 
        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results