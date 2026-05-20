# file: strategies/parabolic_sar_strategy.py

import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class ParabolicSarStrategy:
    """Parabolic SAR reversal — all 5 bugs fixed."""
 
    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 start=0.02, increment=0.02, maximum=0.2,
                 max_intraday_loss_pct=1.0, take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.start             = start
        self.increment         = increment
        self.maximum           = maximum
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0
 
    def _calc_psar(self, df):
        n = len(df)
        sar = np.full(n, np.nan); ep = np.full(n, np.nan)
        af  = np.full(n, self.start); up = np.full(n, True, dtype=bool)
 
        if df["close"].iloc[1] > df["close"].iloc[0]:
            up[1] = True;  ep[1] = df["high"].iloc[1]; sar[1] = df["low"].iloc[0]
        else:
            up[1] = False; ep[1] = df["low"].iloc[1];  sar[1] = df["high"].iloc[0]
 
        for i in range(2, n):
            sar[i] = sar[i-1] + af[i-1]*(ep[i-1]-sar[i-1])
            up[i]  = up[i-1]; ep[i] = ep[i-1]; af[i] = af[i-1]
 
            if up[i]:
                if df["low"].iloc[i] < sar[i]:
                    up[i]=False; sar[i]=max(ep[i-1],df["high"].iloc[i])
                    ep[i]=df["low"].iloc[i]; af[i]=self.start
            else:
                if df["high"].iloc[i] > sar[i]:
                    up[i]=True; sar[i]=min(ep[i-1],df["low"].iloc[i])
                    ep[i]=df["high"].iloc[i]; af[i]=self.start
 
            if up[i]==up[i-1]:
                if up[i] and df["high"].iloc[i] > ep[i]:
                    ep[i]=df["high"].iloc[i]; af[i]=min(af[i]+self.increment,self.maximum)
                elif not up[i] and df["low"].iloc[i] < ep[i]:
                    ep[i]=df["low"].iloc[i];  af[i]=min(af[i]+self.increment,self.maximum)
 
            if up[i]:
                sar[i]=min(sar[i], df["low"].iloc[i-1])
                if i>=2: sar[i]=min(sar[i], df["low"].iloc[i-2])
            else:
                sar[i]=max(sar[i], df["high"].iloc[i-1])
                if i>=2: sar[i]=max(sar[i], df["high"].iloc[i-2])
 
        return pd.Series(sar, index=df.index), pd.Series(up, index=df.index)
 
    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < 3:
            return {"error": "Not enough data (need ≥ 3 bars)"}
        required = ["open", "high", "low", "close", "open_time_utc"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
 
        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])
        df["sar"], df["up"] = self._calc_psar(df)
 
        equity = [self.initial_capital]; position = 0; entry_price = 0.0; entry_time = None
        trades: list = []
 
        for i in range(2, len(df)):
            row = df.iloc[i]; prev = df.iloc[i-1]
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
 
            if row["up"] and not prev["up"] and position <= 0:
                if position == -1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["sar"], dt, self.position_size_pct, "psar_flip")
                position = 1; entry_price = max(row["open"], row["sar"]); entry_time = dt
            elif not row["up"] and prev["up"] and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["sar"], dt, self.position_size_pct, "psar_flip")
                position = -1; entry_price = min(row["open"], row["sar"]); entry_time = dt
 
            equity.append(eq)
 
        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last["open_time_utc"], self.position_size_pct, "end_of_data")
            equity[-1] = eq
 
        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results
 