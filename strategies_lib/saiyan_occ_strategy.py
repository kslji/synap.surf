# file: strategies/saiyan_occ_strategy.py

import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period



class SaiyanOCCStrategy:
    """Saiyan OCC close/open MA crossover — all 5 bugs fixed."""
 
    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 basis_len=2, ma_type="ALMA", use_higher_tf=True, higher_mult=8,
                 tp1_pct=1.0, tp1_qty_pct=50.0, tp2_pct=1.5, tp2_qty_pct=30.0,
                 tp3_pct=2.0, tp3_qty_pct=20.0, sl_pct=0.5,
                 min_bars_between=1, max_hold_bars=0, take_profit_pct=2.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.basis_len         = basis_len
        self.ma_type           = ma_type.upper()
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0
        self.min_bars_between  = min_bars_between
        self.max_hold          = max_hold_bars
 
    def _ma(self, s):
        n = self.basis_len
        if self.ma_type == "SMA":  return s.rolling(n).mean()
        alpha = 2/(n+1)
        return s.ewm(alpha=alpha, adjust=False).mean()
 
    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < self.basis_len*2:
            return {"error": "Not enough data"}
        required = ["open", "high", "low", "close", "open_time_utc"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
 
        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])
        close_ma = self._ma(df["close"]); open_ma = self._ma(df["open"])
        df["long_sig"]  = (df["close"]>open_ma) & (df["close"].shift(1)<=open_ma.shift(1))
        df["short_sig"] = (df["close"]<open_ma) & (df["close"].shift(1)>=open_ma.shift(1))
 
        equity = [self.initial_capital]; position = 0.0; entry_price = 0.0; entry_time = None
        last_sig_idx = -9999
        trades: list = []
 
        for i in range(1, len(df)):
            row = df.iloc[i]; dt = row["open_time_utc"]; eq = equity[-1]
 
            if position != 0:
                sl = entry_price*(1-self.sl_pct) if position>0 else entry_price*(1+self.sl_pct)
                tp = entry_price*(1+self.take_profit_pct/100) if position>0 else entry_price*(1-self.take_profit_pct/100)
                hit = resolve_exit(row, int(position), sl, tp)
                if hit == "sl":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, int(position), entry_price, entry_time, sl, dt, self.position_size_pct, "sl_hit")
                    equity.append(eq); continue
                if hit == "tp":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, int(position), entry_price, entry_time, tp, dt, self.position_size_pct, "take_profit")
 
            if self.max_hold>0 and position!=0 and (i-last_sig_idx)>=self.max_hold:
                eq, position, entry_price, entry_time = close_trade(trades, eq, int(position), entry_price, entry_time, row["close"], dt, self.position_size_pct, "time_exit")
 
            gap = i-last_sig_idx >= self.min_bars_between
            long_sig  = bool(row["long_sig"])  and gap
            short_sig = bool(row["short_sig"]) and gap
 
            if long_sig and position <= 0:
                if position < 0:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, -1, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position=1.0; entry_price=row["close"]; entry_time=dt; last_sig_idx=i
            elif short_sig and position >= 0:
                if position > 0:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, 1, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position=-1.0; entry_price=row["close"]; entry_time=dt; last_sig_idx=i
 
            equity.append(eq)
 
        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], int(position), entry_price, entry_time, last["close"], last["open_time_utc"], self.position_size_pct, "end_of_data")
            equity[-1] = eq
 
        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results
 
 