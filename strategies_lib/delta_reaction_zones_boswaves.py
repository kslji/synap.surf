# file: strategies_lib/delta_reaction_zones_boswaves.py
import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class DeltaReactionZonesStrategy:
    """Delta Reaction Zones [BOSWaves] — all 5 bugs fixed."""

    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 pivot_length=12, delta_smooth=3, atr_length=14, atr_mult=0.35,
                 max_zones=8, merge_zones=False, min_bars_between=5,
                 max_hold_bars=0, take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.pivot_len         = pivot_length
        self.delta_smooth      = delta_smooth
        self.atr_len           = atr_length
        self.atr_mult          = atr_mult
        self.max_zones         = max_zones
        self.min_bars_between  = min_bars_between
        self.max_hold          = max_hold_bars
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0

    def _atr(self, df):
        hl  = df["high"] - df["low"]
        hc  = np.abs(df["high"] - df["close"].shift())
        lc  = np.abs(df["low"]  - df["close"].shift())
        return pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(self.atr_len).mean()

    def _delta(self, df):
        sign = np.sign(df["close"] - df["open"])
        raw  = sign * df["volume"].fillna(0)
        if self.delta_smooth > 1:
            df["cum_delta"] = raw.ewm(alpha=2 / (self.delta_smooth + 1), adjust=False).mean().cumsum()
        else:
            df["cum_delta"] = raw.cumsum()
        return df

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        min_bars = self.pivot_len * 2 + self.atr_len
        if len(df) < min_bars:
            return {"error": f"Not enough data (need >= {min_bars} bars)",
                    "final_equity": self.initial_capital, "total_return_%": 0.0,
                    "max_drawdown_%": 0.0, "n_trades": 0, "win_rate_%": 0.0,
                    "trade_log": pd.DataFrame(), "equity_curve": pd.Series([self.initial_capital])}

        required = ["open", "high", "low", "close", "volume"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        df = df.copy().reset_index(drop=True)
        tc = "open_time_utc" if "open_time_utc" in df.columns else "timestamp"
        if tc in df.columns:
            df[tc] = pd.to_datetime(df[tc])

        df    = self._delta(df)
        df["atr"] = self._atr(df)
        w     = 2 * self.pivot_len + 1
        df["ph"] = df["cum_delta"].rolling(w, center=True).max() == df["cum_delta"]
        df["pl"] = df["cum_delta"].rolling(w, center=True).min() == df["cum_delta"]

        equity = [self.initial_capital]
        position = 0; entry_price = 0.0; entry_time = None
        last_signal_idx = -9999; zones = []
        trades: list = []

        for i in range(min_bars, len(df)):
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

            # Zone creation
            hw = row["atr"] * self.atr_mult if pd.notna(row["atr"]) else 0
            if bool(row["ph"]):
                zones.append({"top": row["high"] + hw, "bottom": row["high"] - hw, "is_lower": False})
            if bool(row["pl"]):
                zones.append({"top": row["low"] + hw, "bottom": row["low"] - hw, "is_lower": True})
            zones = zones[-self.max_zones:]
            zones = [z for z in zones if not ((z["is_lower"] and row["close"] < z["bottom"]) or (not z["is_lower"] and row["close"] > z["top"]))]

            prev_close = df.iloc[i - 1]["close"]
            bull_sig = any(z["is_lower"]     and prev_close < (z["top"]+z["bottom"])/2 and row["close"] > (z["top"]+z["bottom"])/2 for z in zones)
            bear_sig = any(not z["is_lower"] and prev_close > (z["top"]+z["bottom"])/2 and row["close"] < (z["top"]+z["bottom"])/2 for z in zones)
            gap      = i - last_signal_idx >= self.min_bars_between

            if bull_sig and gap and position <= 0:
                if position == -1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position = 1; entry_price = row["close"]; entry_time = dt; last_signal_idx = i
            elif bear_sig and gap and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position = -1; entry_price = row["close"]; entry_time = dt; last_signal_idx = i

            equity.append(eq)

        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last.get(tc), self.position_size_pct, "end_of_data")
            equity[-1] = eq

        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results