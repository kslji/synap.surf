# file: strategies/adx_breakout.py
import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class AdxBreakoutStrategy:
    """Rob Booker ADX Breakout"""
 
    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 adx_period=14, adx_smooth=14, adx_lower_level=18.0,
                 box_lookback=20, profit_multiple=1.0, stop_multiple=0.5,
                 enable_direction=0, max_intraday_loss_pct=1.0,
                 take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.adx_period        = adx_period
        self.adx_smooth        = adx_smooth
        self.adx_lower_level   = adx_lower_level
        self.box_lookback      = box_lookback
        self.profit_multiple   = profit_multiple
        self.stop_multiple     = stop_multiple
        self.enable_direction  = enable_direction
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0
 
    def _adx(self, df):
        tr = pd.concat([df["high"]-df["low"],
                        (df["high"]-df["close"].shift(1)).abs(),
                        (df["low"] -df["close"].shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/self.adx_period, adjust=False).mean()
        up   = df["high"].diff(); dn = -df["low"].diff()
        pdm  = np.where((up>dn)&(up>0), up, 0)
        mdm  = np.where((dn>up)&(dn>0), dn, 0)
        pdi  = 100*pd.Series(pdm).ewm(alpha=1/self.adx_period,adjust=False).mean()/atr
        mdi  = 100*pd.Series(mdm).ewm(alpha=1/self.adx_period,adjust=False).mean()/atr
        dx   = 100*(pdi-mdi).abs()/(pdi+mdi).replace(0,float("nan"))
        return dx.ewm(alpha=1/self.adx_smooth, adjust=False).mean()
 
    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        min_len = max(self.box_lookback, self.adx_period*2)
        if len(df) < min_len:
            return {"error": f"Not enough data (need ≥ {min_len} bars)"}
        required = ["open", "high", "low", "close", "open_time_utc"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
 
        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])
        df["adx"] = self._adx(df)
        df["in_consol"] = df["adx"] < self.adx_lower_level
 
        equity = [self.initial_capital]; position = 0; entry_price = 0.0; entry_time = None
        box_upper = box_lower = np.nan
        trades: list = []
 
        for i in range(min_len, len(df)):
            row = df.iloc[i]; dt = row["open_time_utc"]; eq = equity[-1]
 
            if position != 0:
                sl = entry_price*(1-self.sl_pct) if position==1 else entry_price*(1+self.sl_pct)
                tp = entry_price*(1+self.take_profit_pct/100) if position==1 else entry_price*(1-self.take_profit_pct/100)
                hit = resolve_exit(row, position, sl, tp)
                if hit == "sl":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, sl, dt, self.position_size_pct, "sl_hit")
                    box_upper = box_lower = np.nan; equity.append(eq); continue
                if hit == "tp":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, tp, dt, self.position_size_pct, "take_profit")
                    box_upper = box_lower = np.nan
 
            if position == 0 and row["in_consol"]:
                box_upper = df["high"].iloc[i-self.box_lookback:i].max()
                box_lower = df["low"].iloc[i-self.box_lookback:i].min()
 
            bw = box_upper - box_lower if not np.isnan(box_upper) else 0
 
            long_ok  = position==0 and row["close"]>box_upper and row["in_consol"] and self.enable_direction in (0,1)
            short_ok = position==0 and row["close"]<box_lower and row["in_consol"] and self.enable_direction in (0,-1)
 
            if long_ok:
                position=1; entry_price=row["close"]; entry_time=dt
            elif short_ok:
                position=-1; entry_price=row["close"]; entry_time=dt
 
            # Box-width based exits for open positions
            if position == 1:
                sl_b = entry_price - self.stop_multiple*bw
                tp_b = entry_price + self.profit_multiple*bw
                if row["low"] <= sl_b:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, sl_b, dt, self.position_size_pct, "stop_loss")
                    box_upper=box_lower=np.nan
                elif row["high"] >= tp_b:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, tp_b, dt, self.position_size_pct, "take_profit")
                    box_upper=box_lower=np.nan
            elif position == -1:
                sl_b = entry_price + self.stop_multiple*bw
                tp_b = entry_price - self.profit_multiple*bw
                if row["high"] >= sl_b:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, sl_b, dt, self.position_size_pct, "stop_loss")
                    box_upper=box_lower=np.nan
                elif row["low"] <= tp_b:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, tp_b, dt, self.position_size_pct, "take_profit")
                    box_upper=box_lower=np.nan
 
            equity.append(eq)
 
        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last["open_time_utc"], self.position_size_pct, "end_of_data")
            equity[-1] = eq
 
        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results