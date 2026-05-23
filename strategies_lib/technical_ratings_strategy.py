# file: strategies/technical_rating_approx.py

import pandas as pd
import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class TechnicalRatingApproxStrategy:
    """Technical Rating composite score strategy"""
 
    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 strong_bound=0.5, weak_bound=0.1,
                 use_ma_score=True, use_osc_score=True,
                 atr_period=14, sl_atr_mult=3.0,
                 trail_activate_atr=5.0, trail_offset_atr=2.0,
                 max_intraday_loss_pct=1.5, take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.strong_bound      = strong_bound
        self.use_ma_score      = use_ma_score
        self.use_osc_score     = use_osc_score
        self.atr_period        = atr_period
        self.sl_atr_mult       = sl_atr_mult
        self.trail_activate    = trail_activate_atr
        self.trail_offset      = trail_offset_atr
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0
 
    def _rating(self, df):
        score = pd.Series(0.0, index=df.index)
        if self.use_ma_score:
            for span in [10,20,50,100,200]:
                ema = df["close"].ewm(span=span,adjust=False).mean()
                score += np.where(df["close"]>ema, 0.15, -0.15)
        if self.use_osc_score:
            delta = df["close"].diff()
            gain  = delta.where(delta>0,0).rolling(14).mean()
            loss  = (-delta.where(delta<0,0)).rolling(14).mean()
            rsi   = 100 - (100/(1+gain/loss.replace(0,np.nan)))
            score += np.where(rsi>70, -0.3, np.where(rsi<30, 0.3, 0.0))
        return score.clip(-1,1)
 
    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < 214:
            return {"error": "Not enough data (need ≥ 214 bars)"}
        required = ["open", "high", "low", "close", "open_time_utc"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
 
        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])
        df["rating"] = self._rating(df)
        tr = pd.concat([df["high"]-df["low"],
                        (df["high"]-df["close"].shift(1)).abs(),
                        (df["low"] -df["close"].shift(1)).abs()], axis=1).max(axis=1)
        df["atr"] = tr.rolling(self.atr_period).mean()
 
        equity = [self.initial_capital]; position = 0; entry_price = 0.0; entry_time = None
        high_since = 0.0
        trades: list = []
 
        for i in range(1, len(df)):
            row = df.iloc[i]; dt = row["open_time_utc"]; eq = equity[-1]
 
            if position != 0:
                sl = entry_price*(1-self.sl_pct) if position==1 else entry_price*(1+self.sl_pct)
                tp = entry_price*(1+self.take_profit_pct/100) if position==1 else entry_price*(1-self.take_profit_pct/100)
                hit = resolve_exit(row, position, sl, tp)
                if hit == "sl":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, sl, dt, self.position_size_pct, "sl_hit")
                    high_since=0; equity.append(eq); continue
                if hit == "tp":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, tp, dt, self.position_size_pct, "take_profit")
                    high_since=0
 
            if position == 0:
                if row["rating"] > self.strong_bound:
                    position=1; entry_price=row["close"]; entry_time=dt; high_since=row["high"]
                elif row["rating"] < -self.strong_bound:
                    position=-1; entry_price=row["close"]; entry_time=dt
            elif position == 1:
                high_since = max(high_since, row["high"])
                atr_v = row["atr"] if not pd.isna(row["atr"]) else 0
                sl_atr = entry_price - self.sl_atr_mult*atr_v
                trail_trig = entry_price + self.trail_activate*atr_v
                trail_stop = high_since - self.trail_offset*atr_v
                if row["low"] <= sl_atr:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, 1, entry_price, entry_time, sl_atr, dt, self.position_size_pct, "stop_loss")
                    high_since=0
                elif row["high"] >= trail_trig and row["low"] <= trail_stop:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, 1, entry_price, entry_time, trail_stop, dt, self.position_size_pct, "trailing_stop")
                    high_since=0
 
            equity.append(eq)
 
        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last["open_time_utc"], self.position_size_pct, "end_of_data")
            equity[-1] = eq
 
        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results
 