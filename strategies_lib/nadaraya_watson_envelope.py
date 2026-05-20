# file: strategies_lib/nadaraya_watson_envelope.py

import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class NadarayaWatsonEnvelopeStrategy:
    """Nadaraya-Watson Envelope mean-reversion — all 5 bugs fixed."""
 
    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 window_size=500, bandwidth=8.0, multiplier=3.0,
                 take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.window_size       = window_size
        self.bandwidth         = bandwidth
        self.multiplier        = multiplier
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0
 
    def _nw(self, src):
        n   = len(src); out = np.full(n, np.nan); sv = src.values
        for i in range(n):
            start = max(0, i-self.window_size+1)
            sub   = sv[start:i+1]; m = len(sub)
            x     = np.arange(m) - (m-1)
            w     = np.exp(-(x**2)/(2*self.bandwidth**2))
            sw    = w.sum()
            out[i] = np.dot(sub, w)/sw if sw else sub[-1]
        return pd.Series(out, index=src.index)
 
    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < 10:
            return {"error": "Not enough data"}
        tc = "open_time_utc" if "open_time_utc" in df.columns else "timestamp"
        df = df.copy().reset_index(drop=True)
        if tc in df.columns:
            df[tc] = pd.to_datetime(df[tc])
 
        nw    = self._nw(df["close"])
        mae   = (df["close"]-nw).abs().rolling(self.window_size, min_periods=1).mean()
        upper = nw + mae*self.multiplier
        lower = nw - mae*self.multiplier
        df["upper"] = upper; df["lower"] = lower
 
        equity = [self.initial_capital]; position = 0; entry_price = 0.0; entry_time = None
        trades: list = []
 
        for i in range(1, len(df)):
            row = df.iloc[i]; prev = df.iloc[i-1]
            dt = row.get(tc); eq = equity[-1]
 
            if position != 0:
                sl = entry_price*(1-self.sl_pct) if position==1 else entry_price*(1+self.sl_pct)
                tp = entry_price*(1+self.take_profit_pct/100) if position==1 else entry_price*(1-self.take_profit_pct/100)
                hit = resolve_exit(row, position, sl, tp)
                if hit == "sl":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, sl, dt, self.position_size_pct, "sl_hit")
                    equity.append(eq); continue
                if hit == "tp":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, tp, dt, self.position_size_pct, "take_profit")
 
            long_sig  = (prev["close"] < prev["lower"]) and (row["close"] > row["lower"])
            short_sig = (prev["close"] > prev["upper"]) and (row["close"] < row["upper"])
 
            if long_sig and position <= 0:
                if position == -1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "signal_flip")
                position = 1; entry_price = row["close"]; entry_time = dt
            elif short_sig and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "signal_flip")
                position = -1; entry_price = row["close"]; entry_time = dt
 
            equity.append(eq)
 
        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last.get(tc), self.position_size_pct, "end_of_data")
            equity[-1] = eq
 
        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results