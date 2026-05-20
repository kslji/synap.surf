# file: strategies_lib/ichimoku_cloud_strategy.py
import pandas as pd
from typing import Dict, Any
from utils.base_strategy import build_results, resolve_exit, close_trade
from utils.backtest_ohlc import get_win_loss_by_period


class IchimokuCloudStrategy:
    """Ichimoku Cloud trend-following — all 5 bugs fixed."""

    def __init__(self, tenkan_period=9, kijun_period=26, senkou_b_period=52,
                 initial_capital=1000.0, position_size_pct=1.0,
                 take_profit_pct=2.0, sl_pct=1.0):
        self.tenkan_period    = tenkan_period
        self.kijun_period     = kijun_period
        self.senkou_b_period  = senkou_b_period
        self.initial_capital  = initial_capital
        self.position_size_pct = position_size_pct
        self.take_profit_pct  = take_profit_pct
        self.sl_pct           = sl_pct / 100.0

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        min_bars = self.senkou_b_period + self.kijun_period
        if len(df) < min_bars:
            return {"error": f"Not enough data (minimum ~{min_bars} bars)"}

        required = ["open_time_utc", "open", "high", "low", "close"]
        missing  = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        df = df.copy().reset_index(drop=True)
        df["open_time_utc"] = pd.to_datetime(df["open_time_utc"])

        # Ichimoku calculation
        df["tenkan"]   = (df["high"].rolling(self.tenkan_period).max()  + df["low"].rolling(self.tenkan_period).min())  / 2
        df["kijun"]    = (df["high"].rolling(self.kijun_period).max()   + df["low"].rolling(self.kijun_period).min())   / 2
        df["span_a"]   = ((df["tenkan"] + df["kijun"]) / 2).shift(self.kijun_period)
        df["span_b"]   = ((df["high"].rolling(self.senkou_b_period).max() + df["low"].rolling(self.senkou_b_period).min()) / 2).shift(self.kijun_period)

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

            if pd.isna(row["span_a"]) or pd.isna(row["span_b"]):
                equity.append(eq); continue

            close      = row["close"]
            prev_close = df.iloc[i - 1]["close"]
            tenkan     = row["tenkan"]
            kijun      = row["kijun"]
            cloud_top  = max(row["span_a"], row["span_b"])
            cloud_bot  = min(row["span_a"], row["span_b"])

            # ── Entry ─────────────────────────────────────────────────────────
            if position == 0:
                if close > cloud_top and tenkan > kijun and prev_close <= cloud_top:
                    position = 1; entry_price = close; entry_time = dt
                elif close < cloud_bot and tenkan < kijun and prev_close >= cloud_bot:
                    position = -1; entry_price = close; entry_time = dt

            # ── Kijun-sen exit (BUG 2 — no PnL gate) ────────────────────────
            elif position != 0:
                should_exit = (position == 1 and close < kijun) or (position == -1 and close > kijun)
                if should_exit:
                    eq, position, entry_price, entry_time = close_trade(
                        trades, eq, position, entry_price, entry_time,
                        close, dt, self.position_size_pct, "kijun_exit")

            equity.append(eq)                        # BUG 3

        if position != 0:
            last = df.iloc[-1]
            eq, _, _, _ = close_trade(trades, equity[-1], position, entry_price, entry_time, last["close"], last["open_time_utc"], self.position_size_pct, "end_of_data")
            equity[-1] = eq

        results = build_results(equity, trades, self.initial_capital)
        results.update(get_win_loss_by_period(results["trade_log"]))
        return results