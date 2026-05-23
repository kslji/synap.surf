# file: strategies_lib/future_swing_bigbeluga.py
import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class FutureSwingBigBelugaStrategy:
    """Future Swing [BigBeluga]"""

    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 swing_len=30, hist_samples=5, calc_type="Average",
                 min_bars_between=10, use_projection_tp=False,
                 restrict_repeated=True, max_hold_bars=0,
                 take_profit_pct=2.0, sl_pct=1.0):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.swing_len         = swing_len
        self.samples           = hist_samples
        self.calc_type         = calc_type
        self.min_bars_between  = min_bars_between
        self.restrict_repeated = restrict_repeated
        self.use_projection_tp = use_projection_tp
        self.max_hold          = max_hold_bars
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0

    def _projection(self, past_pcs, price, is_up):
        if not past_pcs:
            return np.nan
        pct = {"Average": np.mean, "Median": np.median}.get(self.calc_type, np.mean)(past_pcs)
        return price * (1 + pct / 100) if is_up else price * (1 - pct / 100)

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < self.swing_len + 1:
            return {"error": f"Not enough data (need >= {self.swing_len + 1} bars)",
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

        df["H"]  = df["high"].rolling(self.swing_len).max()
        df["L"]  = df["low"].rolling(self.swing_len).min()
        df["ph"] = (df["high"].shift(1) == df["H"].shift(1)) & (df["high"] < df["high"].shift(1))
        df["pl"] = (df["low"].shift(1)  == df["L"].shift(1)) & (df["low"]  > df["low"].shift(1))
        df["ph_val"] = np.where(df["ph"], df["high"].shift(1), np.nan)
        df["pl_val"] = np.where(df["pl"], df["low"].shift(1),  np.nan)

        equity = [self.initial_capital]
        position = 0; entry_price = 0.0; entry_time = None
        last_signal_idx = -9999; last_direction = 0; past_pcs = []; current_tp = np.nan
        trades: list = []

        for i in range(self.swing_len, len(df)):
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
                    current_tp = np.nan

            if self.max_hold > 0 and position != 0 and (i - last_signal_idx) >= self.max_hold:
                eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "time_exit")

            if self.use_projection_tp and position != 0 and not np.isnan(current_tp):
                hit_proj = (position == 1 and row["high"] >= current_tp) or (position == -1 and row["low"] <= current_tp)
                if hit_proj:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, current_tp, dt, self.position_size_pct, "tp_projection")
                    current_tp = np.nan

            gap       = i - last_signal_idx >= self.min_bars_between
            long_sig  = bool(row["pl"]) and gap and (not self.restrict_repeated or last_direction != 1)
            short_sig = bool(row["ph"]) and gap and (not self.restrict_repeated or last_direction != -1)

            for sig in [long_sig, short_sig]:
                if sig:
                    ph_v = pd.Series(df["ph_val"].iloc[:i+1]).ffill().iloc[-1]
                    pl_v = pd.Series(df["pl_val"].iloc[:i+1]).ffill().iloc[-1]
                    if not np.isnan(ph_v) and not np.isnan(pl_v):
                        pc = abs((ph_v - pl_v) / min(ph_v, pl_v)) * 100
                        past_pcs = (past_pcs + [pc])[-self.samples:]
                    break

            if long_sig and position <= 0:
                if position == -1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position = 1; entry_price = row["close"]; entry_time = dt; last_signal_idx = i; last_direction = 1
                current_tp = self._projection(past_pcs, entry_price, True) if self.use_projection_tp else np.nan
            elif short_sig and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "opposite_signal")
                position = -1; entry_price = row["close"]; entry_time = dt; last_signal_idx = i; last_direction = -1
                current_tp = self._projection(past_pcs, entry_price, False) if self.use_projection_tp else np.nan

            equity.append(eq)

        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last.get(tc), self.position_size_pct, "end_of_data")
            equity[-1] = eq

        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results