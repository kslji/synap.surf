import pandas as pd
from typing import Dict, Any, List, Tuple

def resolve_exit(row: pd.Series, position: int, sl: float, tp: float) -> str:
    """
    Evaluates Stop Loss and Take Profit levels within a given candle.
    Returns "sl" if Stop Loss hit, "tp" if Take Profit hit, or None.
    """
    low, high = row["low"], row["high"]
    
    if position == 1:
        # Long position
        if low <= sl:
            return "sl"
        if high >= tp:
            return "tp"
    elif position == -1:
        # Short position
        if high >= sl:
            return "sl"
        if low <= tp:
            return "tp"
            
    return None

def close_trade(
    trades: List[Dict[str, Any]], 
    eq: float, 
    position: int, 
    entry_price: float, 
    entry_time: Any, 
    exit_price: float, 
    dt: Any, 
    position_size_pct: float, 
    reason: str
) -> Tuple[float, int, float, Any]:
    """
    Calculates PNL, updates account equity, logs the trade, and returns the new state.
    Returns: (new_equity, new_position (0), new_entry_price (0.0), new_entry_time (None))
    """
    # Calculate PNL percentage based on entry
    if position == 1:
        pnl_pct = (exit_price - entry_price) / entry_price
    else:
        pnl_pct = (entry_price - exit_price) / entry_price
        
    # Calculate actual dollar PNL
    position_size = eq * position_size_pct
    pnl_usd = position_size * pnl_pct
    
    new_eq = eq + pnl_usd
    
    trades.append({
        "entry_time": entry_time,
        "exit_time": dt,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "position": position,
        "pnl_pct": pnl_pct * 100,
        "pnl_usd": pnl_usd,
        "reason": reason
    })
    
    return new_eq, 0, 0.0, None

def build_results(equity: List[float], trades: List[Dict[str, Any]], initial_capital: float) -> Dict[str, Any]:
    """
    Calculates total PNL, win rate, and max drawdown from the equity curve.
    Returns the standard results dictionary.
    """
    total_trades = len(trades)
    win_trades = sum(1 for t in trades if t["pnl_usd"] > 0)
    
    win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0.0
    total_pnl = equity[-1] - initial_capital
    
    # Calculate Max Drawdown
    peak = initial_capital
    max_dd = 0.0
    for eq in equity:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd:
            max_dd = dd
            
    return {
        "metrics": {
            "winRate": round(win_rate, 1),
            "totalPnl": round(total_pnl, 2),
            "drawdown": round(max_dd, 1),
            "trades": total_trades
        },
        "trade_log": trades
    }
