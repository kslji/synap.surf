# file: strategies_lib/rsi_strategy.py
import pandas as pd
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period
 
 
class RsiReversalStrategy:
    """RSI Reversal"""
 
    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 rsi_length=14, rsi_oversold=30.0, rsi_overbought=70.0,
                 max_intraday_loss_pct=1.0, take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.rsi_length        = rsi_length
        self.rsi_oversold      = rsi_oversold
        self.rsi_overbought    = rsi_overbought
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0
 
    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < self.rsi_length + 2:
            return {"error": "Not enough data for RSI"}
        required = ["open", "high", "low", "close", "open_time_utc"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
 
        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])
 
        delta = df["close"].diff()
        gain  = delta.where(delta > 0, 0).rolling(self.rsi_length).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(self.rsi_length).mean()
        df["rsi"] = 100 - (100 / (1 + gain / loss.replace(0, float("nan"))))
 
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
 
            long_sig  = (prev["rsi"] <= self.rsi_oversold)  and (row["rsi"] > self.rsi_oversold)
            short_sig = (prev["rsi"] >= self.rsi_overbought) and (row["rsi"] < self.rsi_overbought)
 
            if long_sig and position <= 0:
                if position == -1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position = 1; entry_price = row["close"]; entry_time = dt
            elif short_sig and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position = -1; entry_price = row["close"]; entry_time = dt
 
            equity.append(eq)
 
        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last["open_time_utc"], self.position_size_pct, "end_of_data")
            equity[-1] = eq
 
        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results
 