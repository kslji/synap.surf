# file: strategies_lib/trama_strategy.py

import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period
 
 
class TramaStrategy:
    """TRAMA adaptive moving average"""
 
    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 length=99, take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.length            = length
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0
 
    def _trama(self, df):
        hh    = df["high"].rolling(self.length).max()
        ll    = df["low"].rolling(self.length).min()
        is_hh = (df["high"] == hh).astype(int)
        is_ll = (df["low"]  == ll).astype(int)
        reg   = (is_hh + is_ll).rolling(self.length).sum()
        alpha = (reg / self.length) ** 2
 
        src   = df["close"].values
        a     = alpha.values
        out   = np.full(len(df), np.nan)
        fv    = self.length - 1
        if fv < len(df):
            out[fv] = src[fv]
            for i in range(fv+1, len(df)):
                ai = a[i] if not np.isnan(a[i]) else 0
                out[i] = out[i-1] + ai*(src[i] - out[i-1])
        return pd.Series(out, index=df.index)
 
    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < self.length:
            return {"error": "Not enough data"}
        tc = "open_time_utc" if "open_time_utc" in df.columns else "timestamp"
 
        df = df.copy().reset_index(drop=True)
        if tc in df.columns:
            df[tc] = pd.to_datetime(df[tc])
        df["trama"] = self._trama(df)
 
        equity = [self.initial_capital]; position = 0; entry_price = 0.0; entry_time = None
        trades: list = []
 
        for i in range(self.length, len(df)):
            row = df.iloc[i]; prev = df.iloc[i-1]
            dt = row.get(tc); eq = equity[-1]
            if np.isnan(row["trama"]):
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
 
            long_sig  = (prev["close"] < prev["trama"]) and (row["close"] > row["trama"])
            short_sig = (prev["close"] > prev["trama"]) and (row["close"] < row["trama"])
 
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