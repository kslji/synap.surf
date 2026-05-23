# file: strategies_lib/ict_smc_reversal.py
import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class IctSmcReversalStrategy:
    """ICT/SMC liquidity sweep reversal"""

    def __init__(self, initial_capital=1000.0, position_size_pct=1.0,
                 max_intraday_loss_pct=1.0, take_profit_pct=2.0, sl_pct=1.0,
                 fvg_tolerance_pct=0.4, swing_lookback=12):
        self.initial_capital   = initial_capital
        self.position_size_pct = position_size_pct
        self.take_profit_pct   = take_profit_pct
        self.sl_pct            = sl_pct / 100.0
        self.fvg_tolerance     = fvg_tolerance_pct / 100.0
        self.swing_lookback    = swing_lookback

    def _precompute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Swing high/low
        roll = self.swing_lookback * 2
        df["swing_high"] = df["high"][df["high"] == df["high"].rolling(roll, center=True).max()].ffill()
        df["swing_low"]  = df["low"][df["low"]   == df["low"].rolling(roll, center=True).min()].ffill()
        df["swing_high"] = df["swing_high"].ffill()
        df["swing_low"]  = df["swing_low"].ffill()

        sh1 = df["swing_high"].shift(1).ffill()
        sl1 = df["swing_low"].shift(1).ffill()

        # Liquidity sweeps
        df["liq_sweep_bull"] = (df["low"] < sl1) & (df["close"] > sl1) & (df["close"] > df["open"])
        df["liq_sweep_bear"] = (df["high"] > sh1) & (df["close"] < sh1) & (df["close"] < df["open"])
        return df

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < 20:
            return {"error": "Not enough data (minimum 20 bars)"}

        required = ["open", "high", "low", "close", "open_time_utc"]
        missing  = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])
        df = self._precompute(df)

        equity      = [self.initial_capital]
        position    = 0
        entry_price = 0.0
        entry_time  = None
        trades: list = []

        for i in range(1, len(df)):
            row = df.iloc[i]
            dt  = row["open_time_utc"]               # BUG 4
            eq  = equity[-1]                         # BUG 3

            # ── TP / SL (BUG 5) ──────────────────────────────────────────────
            if position != 0:
                sl  = entry_price * (1 - self.sl_pct) if position == 1 else entry_price * (1 + self.sl_pct)
                tp  = entry_price * (1 + self.take_profit_pct / 100) if position == 1 else entry_price * (1 - self.take_profit_pct / 100)
                hit = resolve_exit(row, position, sl, tp)
                if hit == "sl":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, sl, dt, self.position_size_pct, "sl_hit")
                    equity.append(eq); continue
                if hit == "tp":
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, tp, dt, self.position_size_pct, "take_profit")

            # ── Signals ───────────────────────────────────────────────────────
            bull = bool(row["liq_sweep_bull"]) and (row["close"] > row["open"])
            bear = bool(row["liq_sweep_bear"]) and (row["close"] < row["open"])

            if bull and position <= 0:
                if position == -1:                   # BUG 2
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "signal_flip")
                position = 1; entry_price = row["close"]; entry_time = dt

            elif bear and position >= 0:
                if position == 1:
                    eq, position, entry_price, entry_time = close_trade(trades, eq, position, entry_price, entry_time, row["close"], dt, self.position_size_pct, "signal_flip")
                position = -1; entry_price = row["close"]; entry_time = dt

            equity.append(eq)                        # BUG 3

        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last["open_time_utc"], self.position_size_pct, "end_of_data")
            equity[-1] = eq

        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results