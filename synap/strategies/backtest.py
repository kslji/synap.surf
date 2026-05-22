import numpy as np
import pandas as pd
from typing import Dict, Any, List
from synap.strategies.indicators import compute_rsi, compute_bollinger_bands

def run_simulation(df: pd.DataFrame, strategy_id: str, initial_capital: float = 1000.0, leverage: int = 1) -> Dict[str, Any]:
    """
    Run a historical backtest on OHLCV data using the specified strategy.
    Returns metrics and a list of trades to be plotted on the frontend.
    """
    if df.empty:
        return {"metrics": {"winRate": 0, "totalPnl": 0, "drawdown": 0, "trades": 0}, "trades": []}

    # Prepare numpy arrays for speed
    open_prices = df["open"].to_numpy(dtype=float)
    high_prices = df["high"].to_numpy(dtype=float)
    low_prices = df["low"].to_numpy(dtype=float)
    close_prices = df["close"].to_numpy(dtype=float)
    time_ms = df.get("open_time_ms", df.get("time", df.index)).to_numpy()

    n = len(close_prices)
    position = 0.0 # 0 = flat, >0 = long
    entry_price = 0.0
    capital = initial_capital
    peak_capital = initial_capital
    max_drawdown = 0.0
    
    trades_log = []
    win_trades = 0
    total_trades = 0
    
    fee_rate = 0.0 # No fee, showing pure gross PnL
    
    # Pre-calculate indicators if needed based on strategy
    # For a full simulation we would compute them recursively, but for speed 
    # and simplicity in pandas, we can pre-compute vectorized indicators where possible.
    
    rsi_series = pd.Series(close_prices).apply(lambda x: 50.0) # Placeholder if not used
    bb_upper = pd.Series(close_prices)
    bb_lower = pd.Series(close_prices)
    
    if strategy_id == "rsi_strategy":
        # Vectorized RSI approximation for speed (14 period)
        delta = pd.Series(close_prices).diff()
        gain = delta.clip(lower=0)
        loss = -1 * delta.clip(upper=0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi_series = 100 - (100 / (1 + rs))
        
    elif strategy_id == "bollinger_bands":
        sma = pd.Series(close_prices).rolling(20).mean()
        std = pd.Series(close_prices).rolling(20).std()
        bb_upper = sma + 2 * std
        bb_lower = sma - 2 * std
        
    elif strategy_id == "channel_breakout":
        highest_high = pd.Series(high_prices).rolling(20).max().shift(1)
        lowest_low = pd.Series(low_prices).rolling(20).min().shift(1)

    for i in range(20, n):
        # We need at least 20 periods for indicators to stabilize
        c = close_prices[i]
        o = open_prices[i]
        h = high_prices[i]
        l = low_prices[i]
        prev_c = close_prices[i-1]
        t = int(time_ms[i] / 1000) if "time_ms" in locals() or "open_time_ms" in df.columns else int(i)
        
        signal = 0 # 1 = buy, -1 = sell
        text = ""

        # Strategy Logic Evaluation
        if strategy_id == "bar_up_down":
            # Long when current close > open, open > prev_c
            if c > o and o > prev_c:
                signal = 1
                text = "BarUp"
            # Reverse when current close < open, open < prev_c
            elif c < o and o < prev_c:
                signal = -1
                text = "BarDn"
                
        elif strategy_id == "bollinger_bands":
            # Buy when price pierces below lower band
            if c < bb_lower.iloc[i]:
                signal = 1
                text = "BBLow"
            # Sell when price pushes above upper band
            elif c > bb_upper.iloc[i]:
                signal = -1
                text = "BBHigh"
                
        elif strategy_id == "channel_breakout":
            if c > highest_high.iloc[i]:
                signal = 1
                text = "BreakUp"
            elif c < lowest_low.iloc[i]:
                signal = -1
                text = "BreakDn"
                
        elif strategy_id == "consecutive_up_down":
            # 3 consecutive bullish
            if i >= 3:
                bull1 = close_prices[i] > open_prices[i]
                bull2 = close_prices[i-1] > open_prices[i-1]
                bull3 = close_prices[i-2] > open_prices[i-2]
                
                bear1 = close_prices[i] < open_prices[i]
                bear2 = close_prices[i-1] < open_prices[i-1]
                bear3 = close_prices[i-2] < open_prices[i-2]
                
                if bull1 and bull2 and bull3:
                    signal = 1
                    text = "3xBull"
                elif bear1 and bear2 and bear3:
                    signal = -1
                    text = "3xBear"
                    
        elif strategy_id == "rsi_strategy":
            rsi = rsi_series.iloc[i]
            if rsi < 30:
                signal = 1
                text = "RSI<30"
            elif rsi > 70:
                signal = -1
                text = "RSI>70"
                
        else:
            # Fallback random for unknown strategies just in case
            import random
            if random.random() > 0.95:
                signal = 1 if position == 0 else -1
                text = "Buy" if signal == 1 else "Sell"

        # Trade Execution Simulation
        if signal == 1 and position == 0:
            # Enter Long
            qty = (capital * leverage) / c
            fee = (capital * leverage) * fee_rate
            capital -= fee
            position = qty
            entry_price = c
            
            trades_log.append({
                "time": t,
                "price": c,
                "side": "buy",
                "text": text
            })
            
        elif signal == -1 and position > 0:
            # Exit Long
            exit_value = position * c
            fee = exit_value * fee_rate
            pnl = exit_value - (position * entry_price)
            
            capital = capital + pnl - fee
            
            if pnl > 0:
                win_trades += 1
            total_trades += 1
            
            position = 0.0
            
            trades_log.append({
                "time": t,
                "price": c,
                "side": "sell",
                "text": text
            })
            
        # Drawdown Tracking
        current_equity = capital + (position * c - position * entry_price if position > 0 else 0)
        if current_equity > peak_capital:
            peak_capital = current_equity
        
        drawdown = (peak_capital - current_equity) / peak_capital * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    # Close any open position at the end
    if position > 0:
        c = close_prices[-1]
        t = int(time_ms[-1] / 1000) if "time_ms" in locals() or "open_time_ms" in df.columns else int(n-1)
        exit_value = position * c
        fee = exit_value * fee_rate
        pnl = exit_value - (position * entry_price)
        capital = capital + pnl - fee
        
        if pnl > 0:
            win_trades += 1
        total_trades += 1
        
        trades_log.append({
            "time": t,
            "price": c,
            "side": "sell",
            "text": "Close"
        })

    total_pnl = capital - initial_capital
    win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    metrics = {
        "winRate": round(win_rate, 1),
        "totalPnl": round(total_pnl, 2),
        "drawdown": round(max_drawdown, 1),
        "trades": total_trades
    }
    
    return {
        "metrics": metrics,
        "trades": trades_log
    }
