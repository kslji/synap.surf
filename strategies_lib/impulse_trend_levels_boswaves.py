# file: strategies_lib/impulse_trend_levels_boswaves.py
import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class ImpulseTrendLevelsStrategy:
    """Impulse Trend Levels (BOSWaves)"""

    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 trend_len=19, impulse_len=5, decay_rate=0.99,
                 mad_len=20, band_min=1.5, band_max=1.9,
                 min_bars_between=10, use_retest=False, signal_buffer=10,
                 restrict_repeated=True, max_hold_bars=0,
                 take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.trend_len         = trend_len
        self.impulse_len       = impulse_len
        self.decay_rate        = decay_rate
        self.mad_len           = mad_len
        self.band_min          = band_min
        self.band_max          = band_max
        self.min_bars_between  = min_bars_between
        self.restrict_repeated = restrict_repeated
        self.max_hold          = max_hold_bars
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        min_bars = max(self.trend_len, self.mad_len, self.impulse_len) * 2
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

        alpha = 2 / (self.trend_len + 1)
        df["basis"] = df["close"].ewm(alpha=alpha, adjust=False).mean()
        df["mean"]  = df["close"].rolling(self.mad_len).mean()
        df["mad"]   = (df["close"] - df["mean"]).abs().rolling(self.mad_len).mean()
        df["raw_impulse"] = np.where(df["mad"] > 0,
            (df["close"] - df["close"].shift(self.impulse_len)) / df["mad"], 0)

        imp = np.zeros(len(df))
        for j in range(1, len(df)):
            ar = abs(df["raw_impulse"].iloc[j])
            imp[j] = ar if ar > 1.0 else imp[j - 1] * self.decay_rate
        df["impulse"]    = imp
        df["freshness"]  = np.minimum(df["impulse"] / 2.0, 1.0)
        df["band_mult"]  = self.band_max - (self.band_max - self.band_min) * df["freshness"]
        df["upper"]      = df["basis"] + df["mad"] * df["band_mult"]
        df["lower"]      = df["basis"] - df["mad"] * df["band_mult"]
        df["long_cond"]  = (df["close"] > df["upper"]) & (df["close"].shift(1) <= df["upper"].shift(1))
        df["short_cond"] = (df["close"] < df["lower"]) & (df["close"].shift(1) >= df["lower"].shift(1))

        equity = [self.initial_capital]
        position = 0; entry_price = 0.0; entry_time = None
        last_signal_idx = -9999; last_direction = 0
        trades: list = []

        for i in range(1, len(df)):
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

            gap       = i - last_signal_idx >= self.min_bars_between
            long_sig  = bool(row["long_cond"]) and gap and (not self.restrict_repeated or last_direction != 1)
            short_sig = bool(row["short_cond"]) and gap and (not self.restrict_repeated or last_direction != -1)

            if long_sig and position <= 0:
                if position == -1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position = 1; entry_price = row["close"]; entry_time = dt; last_signal_idx = i; last_direction = 1
            elif short_sig and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position = -1; entry_price = row["close"]; entry_time = dt; last_signal_idx = i; last_direction = -1

            equity.append(eq)

        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last.get(tc), self.position_size_pct, "end_of_data")
            equity[-1] = eq

        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results