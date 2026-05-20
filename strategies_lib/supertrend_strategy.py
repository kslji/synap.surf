# file: strategies/supertrend.py

import pandas as pd
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period

import numpy as np
 
class SupertrendStrategy:
    """Supertrend reversal — all 5 bugs fixed."""
 
    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 period=10, factor=3.0, max_intraday_loss_pct=1.0,
                 take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.period            = period
        self.factor            = factor
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0
 
    def _supertrend(self, df):
        hl2 = (df["high"] + df["low"]) / 2
        tr  = pd.concat([df["high"]-df["low"],
                         (df["high"]-df["close"].shift(1)).abs(),
                         (df["low"] -df["close"].shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(self.period).mean()
        ub_raw = hl2 + self.factor * atr
        lb_raw = hl2 - self.factor * atr
 
        n = len(df)
        ub = ub_raw.values.copy()
        lb = lb_raw.values.copy()
        trend = np.ones(n, dtype=int)
        cl = df["close"].values
 
        for i in range(1, n):
            ub[i] = min(ub_raw.iloc[i], ub[i-1]) if cl[i-1] < ub[i-1] else ub_raw.iloc[i]
            lb[i] = max(lb_raw.iloc[i], lb[i-1]) if cl[i-1] > lb[i-1] else lb_raw.iloc[i]
            if cl[i] > ub[i]:   trend[i] = 1
            elif cl[i] < lb[i]: trend[i] = -1
            else:
                trend[i] = trend[i-1]
                if trend[i] == 1:  lb[i] = max(lb_raw.iloc[i], lb[i-1])
                else:              ub[i] = min(ub_raw.iloc[i], ub[i-1])
 
        return pd.Series(trend, index=df.index)
 
    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < self.period + 2:
            return {"error": f"Not enough data (need ≥ {self.period + 2} bars)"}
        required = ["open", "high", "low", "close", "open_time_utc"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
 
        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])
        df["trend"] = self._supertrend(df)
 
        equity = [self.initial_capital]; position = 0; entry_price = 0.0; entry_time = None
        trades: list = []
 
        for i in range(1, len(df)):
            row = df.iloc[i]; prev = df.iloc[i - 1]
            dt = row["open_time_utc"]; eq = equity[-1]
 
            if position != 0:
                sl = entry_price*(1-self.sl_pct) if position==1 else entry_price*(1+self.sl_pct)
                tp = entry_price*(1+self.take_profit_pct/100) if position==1 else entry_price*(1-self.take_profit_pct/100)
                hit = resolve_exit(row, position, sl, tp)
                if hit == "sl":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, sl, dt, self.position_size_pct, "sl_hit")
                    equity.append(eq); continue
                if hit == "tp":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, tp, dt, self.position_size_pct, "take_profit")
 
            flipped = prev["trend"] != row["trend"]
            long_sig  = flipped and row["trend"] == 1
            short_sig = flipped and row["trend"] == -1
 
            if long_sig and position <= 0:
                if position == -1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "supertrend_flip")
                position = 1; entry_price = row["close"]; entry_time = dt
            elif short_sig and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "supertrend_flip")
                position = -1; entry_price = row["close"]; entry_time = dt
 
            equity.append(eq)
 
        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last["open_time_utc"], self.position_size_pct, "end_of_data")
            equity[-1] = eq
 
        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results
 