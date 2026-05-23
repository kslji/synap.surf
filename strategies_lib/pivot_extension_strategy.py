# file: strategies_lib/pivot_extension_strategy.py
import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period
 
 
class PivotReversalStrategy:
    """Pivot Extension reversal"""
 
    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 left_bars=4, right_bars=2, max_intraday_loss_pct=1.0,
                 take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.left_bars         = left_bars
        self.right_bars        = right_bars
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0
 
    def _pivots(self, df):
        n = len(df); ph = np.full(n, np.nan); pl = np.full(n, np.nan)
        lb, rb = self.left_bars, self.right_bars
        for i in range(lb, n - rb):
            hw = df["high"].iloc[i-lb:i+rb+1]
            lw = df["low"].iloc[i-lb:i+rb+1]
            if df["high"].iloc[i] == hw.max() and (hw.iloc[:lb] < df["high"].iloc[i]).all() and (hw.iloc[lb+1:] < df["high"].iloc[i]).all():
                ph[i] = df["high"].iloc[i]
            if df["low"].iloc[i] == lw.min() and (lw.iloc[:lb] > df["low"].iloc[i]).all() and (lw.iloc[lb+1:] > df["low"].iloc[i]).all():
                pl[i] = df["low"].iloc[i]
        return pd.Series(ph, index=df.index), pd.Series(pl, index=df.index)
 
    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        min_bars = self.left_bars + self.right_bars + 1
        if len(df) < min_bars:
            return {"error": f"Not enough data (need ≥ {min_bars} bars)"}
        required = ["open", "high", "low", "close", "open_time_utc"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
 
        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])
        df["ph"], df["pl"] = self._pivots(df)
 
        equity = [self.initial_capital]; position = 0; entry_price = 0.0; entry_time = None
        trades: list = []
        start = self.left_bars + self.right_bars + 1
 
        for i in range(start, len(df)):
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
 
            long_sig  = not pd.isna(row["pl"])
            short_sig = not pd.isna(row["ph"])
 
            if long_sig and position <= 0:
                if position == -1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_pivot")
                position = 1; entry_price = row["close"]; entry_time = dt
            elif short_sig and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_pivot")
                position = -1; entry_price = row["close"]; entry_time = dt
 
            equity.append(eq)
 
        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last["open_time_utc"], self.position_size_pct, "end_of_data")
            equity[-1] = eq
 
        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results