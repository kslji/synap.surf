# file: strategies/predicta_futures_v4.py

import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class PredictaFuturesStrategy:
    """Predicta Futures V4 confluence strategy — all 5 bugs fixed."""
 
    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 atr_len=14, st_factor=3.0, st_period=10,
                 min_confluence=5, min_vol_ratio=0.8, adx_threshold=25,
                 perfect_only=False, min_bars_between=5, max_hold_bars=0,
                 take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.min_confluence    = min_confluence
        self.min_vol           = min_vol_ratio
        self.perfect_only      = perfect_only
        self.min_bars_between  = min_bars_between
        self.max_hold          = max_hold_bars
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0
        self.st_factor         = st_factor
        self.st_period         = st_period
        self.atr_len           = atr_len
 
    def _atr(self, df, p):
        tr = pd.concat([df["high"]-df["low"],
                        (df["high"]-df["close"].shift(1)).abs(),
                        (df["low"] -df["close"].shift(1)).abs()], axis=1).max(axis=1)
        return tr.rolling(p).mean()
 
    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        min_needed = max(self.st_period, self.atr_len)*2
        if len(df) < min_needed:
            return {"error": f"Not enough data (need ≥ {min_needed} bars)"}
        required = ["open", "high", "low", "close", "volume", "open_time_utc"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
 
        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])
 
        # Supertrend direction
        hl2 = (df["high"]+df["low"])/2
        atr = self._atr(df, self.st_period)
        ub_r = hl2 + self.st_factor*atr; lb_r = hl2 - self.st_factor*atr
        n = len(df); ub = ub_r.values.copy(); lb = lb_r.values.copy()
        dire = np.ones(n, dtype=int); cl = df["close"].values
        for i in range(1,n):
            ub[i] = min(ub_r.iloc[i],ub[i-1]) if cl[i-1]<ub[i-1] else ub_r.iloc[i]
            lb[i] = max(lb_r.iloc[i],lb[i-1]) if cl[i-1]>lb[i-1] else lb_r.iloc[i]
            dire[i] = -1 if cl[i]<lb[i] else (1 if cl[i]>ub[i] else dire[i-1])
        df["is_up"]  = dire == -1
        df["is_down"]= dire ==  1
        df["ema8"]   = df["close"].ewm(span=8, adjust=False).mean()
        df["ema21"]  = df["close"].ewm(span=21, adjust=False).mean()
        df["vol_sma"]= df["volume"].rolling(20).mean()
        df["vol_r"]  = df["volume"] / df["vol_sma"].replace(0, np.nan)
        rng = (df["high"]-df["low"]).replace(0,np.nan)
        df["delta_bull"] = ((df["close"]-df["low"])/rng*df["volume"]) > \
                           ((df["close"]-df["low"])/rng*df["volume"]).ewm(span=10,adjust=False).mean()
        df["delta_bear"] = ~df["delta_bull"]
        df["bull_sig"] = df["is_up"]   & (df["ema8"]>df["ema21"]) & df["delta_bull"]
        df["bear_sig"] = df["is_down"] & (df["ema8"]<df["ema21"]) & df["delta_bear"]
 
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
            long_sig  = bool(row["bull_sig"]) and gap
            short_sig = bool(row["bear_sig"]) and gap
 
            if long_sig and position <= 0:
                if position < 0:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, -1, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position=self.position_size_pct; entry_price=row["close"]; entry_time=dt; last_sig_idx=i
            elif short_sig and position >= 0:
                if position > 0:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, 1, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position=-self.position_size_pct; entry_price=row["close"]; entry_time=dt; last_sig_idx=i
 
            equity.append(eq)
 
        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], int(position), entry_price, entry_time, last["close"], last["open_time_utc"], self.position_size_pct, "end_of_data")
            equity[-1] = eq
 
        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results