# file: strategies/vwap_reversion.py

import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class VwapReversionStrategy:
    """Rolling VWAP mean reversion"""
 
    def __init__(self, rolling_period=48, std_multiplier=2.5,
                 initial_capital=1000.0, position_size_pct=1.0,
                 take_profit_pct=2.0, sl_pct=1.0):
        self.rolling_period    = rolling_period
        self.std_multiplier    = std_multiplier
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0
 
    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < self.rolling_period + 1:
            return {"error": f"Not enough data (need ≥ {self.rolling_period+1} bars)"}
        required = ["open", "high", "low", "close", "volume", "open_time_utc"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
 
        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])
        rp = self.rolling_period
        df["vwap"]  = (df["close"]*df["volume"]).rolling(rp).sum() / df["volume"].rolling(rp).sum()
        df["std"]   = df["close"].rolling(rp).std()
        df["upper"] = df["vwap"] + self.std_multiplier*df["std"]
        df["lower"] = df["vwap"] - self.std_multiplier*df["std"]
 
        equity = [self.initial_capital]; position = 0; entry_price = 0.0; entry_time = None
        trades: list = []
 
        for i in range(1, len(df)):
            row = df.iloc[i]; dt = row["open_time_utc"]; eq = equity[-1]
            if pd.isna(row["vwap"]):
                equity.append(eq); continue
 
            if position != 0:
                sl = entry_price*(1-self.sl_pct) if position==1 else entry_price*(1+self.sl_pct)
                tp = entry_price*(1+self.take_profit_pct/100) if position==1 else entry_price*(1-self.take_profit_pct/100)
                hit = resolve_exit(row, position, sl, tp)
                if hit == "sl":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, sl, dt, self.position_size_pct, "sl_hit")
                    equity.append(eq); continue
                if hit == "tp":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, tp, dt, self.position_size_pct, "take_profit")
 
            # Entry
            if position == 0:
                if row["close"] > row["upper"]:
                    position = -1; entry_price = row["close"]; entry_time = dt
                elif row["close"] < row["lower"]:
                    position =  1; entry_price = row["close"]; entry_time = dt
            # VWAP reversion exit
            elif position != 0:
                should_exit = (position==1 and row["close"]>=row["vwap"]) or \
                              (position==-1 and row["close"]<=row["vwap"])
                if should_exit:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "mean_reversion")
 
            equity.append(eq)
 
        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last["open_time_utc"], self.position_size_pct, "end_of_data")
            equity[-1] = eq
 
        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results