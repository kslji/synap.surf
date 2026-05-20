# file: strategies_lib/luxalgo_msb_ob_kit.py
import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class LuxAlgoMSBOrderBlockStrategy:
    """LuxAlgo MSB + Order Block — all 5 bugs fixed."""

    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 pivot_len=7, z_score_threshold=0.5, min_bars_between_signals=10,
                 restrict_same_direction=True, use_hp_ob_only=False,
                 max_hold_bars=0, take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.pivot_len         = pivot_len
        self.z_threshold       = z_score_threshold
        self.min_bars_between  = min_bars_between_signals
        self.restrict_same     = restrict_same_direction
        self.use_hp_only       = use_hp_ob_only
        self.max_hold          = max_hold_bars
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0

    def _pivots(self, df):
        high = df["high"].values; low = df["low"].values; n = len(df)
        ph = np.full(n, np.nan); pl = np.full(n, np.nan)
        for i in range(self.pivot_len, n - self.pivot_len):
            if high[i] == np.max(high[i - self.pivot_len: i + self.pivot_len + 1]):
                ph[i] = high[i]
            if low[i] == np.min(low[i - self.pivot_len: i + self.pivot_len + 1]):
                pl[i] = low[i]
        df["pivot_high"] = ph; df["pivot_low"] = pl
        return df

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        min_bars = self.pivot_len * 2 + 50
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

        df["price_change"] = df["close"].diff()
        df["avg_change"]   = df["price_change"].rolling(50).mean()
        df["std_change"]   = df["price_change"].rolling(50).std()
        df["momentum_z"]   = (df["price_change"] - df["avg_change"]) / df["std_change"].replace(0, np.nan)
        df = self._pivots(df)
        df["last_ph"] = df["pivot_high"].ffill()
        df["last_pl"] = df["pivot_low"].ffill()
        df["msb_bull"] = (df["close"] > df["last_ph"]) & (df["close"].shift(1) <= df["last_ph"]) & (df["momentum_z"] > self.z_threshold)
        df["msb_bear"] = (df["close"] < df["last_pl"]) & (df["close"].shift(1) >= df["last_pl"]) & (df["momentum_z"] < -self.z_threshold)

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
            long_sig  = bool(row["msb_bull"]) and gap and (not self.restrict_same or last_direction != 1)
            short_sig = bool(row["msb_bear"]) and gap and (not self.restrict_same or last_direction != -1)

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