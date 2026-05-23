# file: strategies/price_channel.py

import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period

class PriceChannelStrategy:
    """Donchian Channel breakout"""
 
    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 channel_length=20, tick_offset=0.01,
                 max_intraday_loss_pct=1.0, take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.channel_length    = channel_length
        self.tick_offset       = tick_offset
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0
 
    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < self.channel_length + 1:
            return {"error": f"Not enough data (need ≥ {self.channel_length + 1} bars)"}
        required = ["open", "high", "low", "close", "open_time_utc"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
 
        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])
        df["upper"] = df["high"].rolling(self.channel_length).max().shift(1)
        df["lower"] = df["low"].rolling(self.channel_length).min().shift(1)
 
        equity = [self.initial_capital]; position = 0; entry_price = 0.0; entry_time = None
        trades: list = []
 
        for i in range(self.channel_length + 1, len(df)):
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
 
            buy_lvl  = row["upper"] + self.tick_offset if not pd.isna(row["upper"]) else float("inf")
            sell_lvl = row["lower"] - self.tick_offset if not pd.isna(row["lower"]) else -float("inf")
 
            if row["high"] >= buy_lvl and position <= 0:
                if position == -1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, buy_lvl, dt, self.position_size_pct, "opposite_breakout")
                position = 1; entry_price = max(row["open"], buy_lvl); entry_time = dt
            elif row["low"] <= sell_lvl and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, sell_lvl, dt, self.position_size_pct, "opposite_breakout")
                position = -1; entry_price = min(row["open"], sell_lvl); entry_time = dt
 
            equity.append(eq)
 
        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last["open_time_utc"], self.position_size_pct, "end_of_data")
            equity[-1] = eq
 
        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results