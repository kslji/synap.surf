# file: strategies_lib/gold_ob_finder_backtest.py
import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class GoldOrderBlockStrategy:
    """Gold Order Block Finder — all 5 bugs fixed."""

    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 swing_length=7, lookback=20, displacement_mult=1.3,
                 min_strength=3.0, max_active_obs=5, rr_ratio=2.0,
                 use_fixed_rr=True, max_hold_bars=0, take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.swing_length      = swing_length
        self.lookback          = lookback
        self.displacement_mult = displacement_mult
        self.min_strength      = min_strength
        self.max_active        = max_active_obs
        self.max_hold          = max_hold_bars
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0

    def _pivots(self, df):
        high = df["high"].values; low = df["low"].values; n = len(df)
        ph = np.full(n, np.nan); pl = np.full(n, np.nan)
        for i in range(self.swing_length, n - self.swing_length):
            s = self.swing_length
            if high[i] == np.max(high[i - s: i + s + 1]):
                ph[i] = high[i]
            if low[i] == np.min(low[i - s: i + s + 1]):
                pl[i] = low[i]
        return pd.Series(ph, index=df.index), pd.Series(pl, index=df.index)

    def _strength(self, disp, zone_h, age, atr):
        if atr <= 0:
            return 5.0
        return min(10.0, min(3.0, disp / atr * 1.2) + min(3.0, 3.0 - abs(zone_h / atr - 1.0) * 2) + max(0.5, 2.0 - age / 100.0))

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        min_bars = self.swing_length * 2 + 10
        if len(df) < min_bars:
            return {"error": f"Not enough data (need >= {min_bars} bars)",
                    "final_equity": self.initial_capital, "total_return_%": 0.0,
                    "max_drawdown_%": 0.0, "n_trades": 0, "win_rate_%": 0.0,
                    "trade_log": pd.DataFrame(), "equity_curve": pd.Series([self.initial_capital])}

        required = ["open", "high", "low", "close"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        df = df.copy().reset_index(drop=True)
        tc = "open_time_utc" if "open_time_utc" in df.columns else "timestamp"
        if tc in df.columns:
            df[tc] = pd.to_datetime(df[tc])
        df["atr"] = (df["high"] - df["low"]).rolling(14).mean().fillna(0)
        ph, pl = self._pivots(df)

        equity = [self.initial_capital]
        position = 0; entry_price = 0.0; entry_time = None
        last_signal_idx = -9999; bull_obs = []; bear_obs = []
        trades: list = []

        for i in range(self.swing_length * 2, len(df)):
            row = df.iloc[i]
            dt  = row.get(tc)
            eq  = equity[-1]

            if position != 0:
                sl  = entry_price * (1 - self.sl_pct) if position == 1 else entry_price * (1 + self.sl_pct)
                tp  = entry_price * (1 + self.take_profit_pct / 100) if position == 1 else entry_price * (1 - self.take_profit_pct / 100)
                hit = resolve_exit(row, position, sl, tp)
                if hit == "sl":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, sl, dt, self.position_size_pct, "sl_hit")
                    equity.append(eq); continue
                if hit == "tp":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, tp, dt, self.position_size_pct, "take_profit")

            if self.max_hold > 0 and position != 0 and (i - last_signal_idx) >= self.max_hold:
                eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "time_exit")

            # Mitigation
            bull_obs = [z for z in bull_obs if row["close"] >= z["bottom"]][-self.max_active:]
            bear_obs = [z for z in bear_obs if row["close"] <= z["top"]][-self.max_active:]

            # New OB detection
            if not np.isnan(ph.iloc[i]):
                for k in range(1, self.lookback + 1):
                    if i - k < 0: break
                    pc = df.iloc[i - k]
                    if pc["close"] > pc["open"]:
                        disp = pc["high"] - ph.iloc[i]; rng = pc["high"] - pc["low"]
                        if disp > rng * self.displacement_mult and rng > 0:
                            s = self._strength(disp, pc["high"] - pc["low"], 0, row["atr"])
                            if s >= self.min_strength:
                                bear_obs.append({"top": pc["high"], "bottom": pc["low"]})
                            break

            if not np.isnan(pl.iloc[i]):
                for k in range(1, self.lookback + 1):
                    if i - k < 0: break
                    pc = df.iloc[i - k]
                    if pc["close"] < pc["open"]:
                        disp = pl.iloc[i] - pc["low"]; rng = pc["high"] - pc["low"]
                        if disp > rng * self.displacement_mult and rng > 0:
                            s = self._strength(disp, pc["high"] - pc["low"], 0, row["atr"])
                            if s >= self.min_strength:
                                bull_obs.append({"top": pc["high"], "bottom": pc["low"]})
                            break

            long_sig  = any(row["low"] <= z["top"] and row["high"] >= z["bottom"] for z in bull_obs)
            short_sig = any(row["low"] <= z["top"] and row["high"] >= z["bottom"] for z in bear_obs)

            if long_sig and position <= 0:
                if position == -1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_ob")
                position = 1; entry_price = row["close"]; entry_time = dt; last_signal_idx = i
            elif short_sig and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_ob")
                position = -1; entry_price = row["close"]; entry_time = dt; last_signal_idx = i

            equity.append(eq)

        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last.get(tc), self.position_size_pct, "end_of_data")
            equity[-1] = eq

        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results