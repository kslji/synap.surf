import sqlite3
import os
import json
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), 'algo_brain.db')

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

def init_db():
    with get_db() as db:
        # Users Table (to store API keys securely later, right now basic storage)
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                wallet_address TEXT PRIMARY KEY,
                private_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Strategies Catalog
        db.execute('''
            CREATE TABLE IF NOT EXISTS strategies (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                tags TEXT
            )
        ''')

        # Strategy Execution State
        db.execute('''
            CREATE TABLE IF NOT EXISTS strategy_state (
                strategy_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'FLAT', -- 'FLAT' or 'IN_TRADE'
                active_coin TEXT,
                active_direction TEXT
            )
        ''')

        # User Subscriptions
        db.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT,
                strategy_id TEXT,
                status TEXT DEFAULT 'WAITING', -- 'WAITING' or 'ACTIVE'
                capital REAL,
                leverage INTEGER,
                timeframe TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(wallet_address, strategy_id)
            )
        ''')

        # Cache Table for Backtest Results
        db.execute('''
            CREATE TABLE IF NOT EXISTS backtest_cache (
                strategy_id TEXT,
                timeframe TEXT,
                metrics_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (strategy_id, timeframe)
            )
        ''')

        # Signals Queue (to decouple strategy processes from execution engine)
        db.execute('''
            CREATE TABLE IF NOT EXISTS signals_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT,
                coin TEXT,
                action TEXT, -- 'OPEN_LONG', 'CLOSE_LONG', 'OPEN_SHORT', 'CLOSE_SHORT'
                price REAL,
                processed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

def seed_strategies():
    strategies = [
        ('bar_up_down', 'Bar Up Down', 'High-performance algorithmic strategy based on price action and consecutive bar reversals.', json.dumps(['Price Action', 'Reversal'])),
        ('bollinger_bands', 'Bollinger Bands', 'Mean reversion strategy trading the edges of standard deviation bands.', json.dumps(['Volatility', 'Mean Reversion'])),
        ('candle_2_closure', 'Candle 2 Closure', 'Strategy waiting for a 2-candle confirmation using LuxAlgo indicators.', json.dumps(['LuxAlgo', 'Confirmation'])),
        ('channel_breakout', 'Channel Breakout', 'Momentum strategy catching breakouts of established price channels.', json.dumps(['Trend', 'Breakout'])),
        ('consecutive_up_down', 'Consecutive Up Down', 'Momentum trading strategy based on sequential candle closures.', json.dumps(['Momentum'])),
        ('delta_reaction', 'Delta Reaction Zones', 'Uses order flow and breakout of structure (BOS) for entries.', json.dumps(['Order Flow', 'BOS'])),
        ('fib_sequence', 'Fibonacci Sequence Grid', 'Level-to-level trading using key Fibonacci sequence zones.', json.dumps(['Levels', 'BigBeluga'])),
        ('future_swing', 'Future Swing', 'Swing trading system designed to catch macro trend reversals.', json.dumps(['Trend', 'Swing'])),
        ('gold_ob_finder', 'Gold OB Finder', 'Identifies institutional order blocks for high-probability entries.', json.dumps(['SMC', 'Order Block'])),
        ('greedy', 'Greedy Strategy', 'Aggressive scalping strategy taking small frequent profits.', json.dumps(['Aggressive', 'Scalp'])),
        ('hyper', 'Hyper Scalper', 'High frequency trading model operating on sub-minute charts.', json.dumps(['High Frequency'])),
        ('ichimoku_cloud', 'Ichimoku Cloud', 'Complex trend-following strategy using Ichimoku Kinko Hyo.', json.dumps(['Trend', 'Complex'])),
        ('ict_smc_reversal', 'ICT SMC Reversal', 'Smart Money Concepts strategy targeting liquidity sweeps.', json.dumps(['SMC', 'Institutional'])),
        ('impulse_trend', 'Impulse Trend Levels', 'Momentum breakouts using proprietary impulse measurements.', json.dumps(['Momentum'])),
        ('inside_bar', 'Inside Bar', 'Classic price action pattern identifying volatility contraction.', json.dumps(['Price Action'])),
        ('luxalgo_msb_ob', 'LuxAlgo MSB/OB Kit', 'Premium LuxAlgo suite mapping market structure breaks.', json.dumps(['Premium', 'SMC'])),
        ('macd', 'MACD Cross', 'Standard MACD moving average convergence divergence crossover.', json.dumps(['Indicator', 'Trend'])),
        ('moving_avg_2_line', 'Moving Avg 2 Line', 'Simple dual moving average crossover trend follower.', json.dumps(['Trend'])),
        ('nadaraya_watson', 'Nadaraya Watson Envelope', 'Non-parametric kernel smoothing envelope for mean reversion.', json.dumps(['Kernel', 'Smoothing'])),
        ('parabolic_sar', 'Parabolic SAR', 'Stop and Reverse system for capturing trending moves.', json.dumps(['Reversal', 'Trend'])),
        ('predicta_futures', 'Predicta Futures v4', 'Advanced machine learning model for directional prediction.', json.dumps(['ML', 'Advanced'])),
        ('rob_booker_adx', 'Rob Booker ADX Breakout', 'Volatility breakout system using the ADX indicator.', json.dumps(['Trend', 'Volatility'])),
        ('rsi_strategy', 'RSI Strategy', 'Oscillator-based strategy identifying overbought and oversold conditions.', json.dumps(['Oscillator', 'OB/OS'])),
        ('saiyan_occ', 'Saiyan OCC', 'Aggressive momentum continuation strategy.', json.dumps(['Momentum'])),
        ('supertrend', 'Supertrend', 'Follows the dominant trend using ATR-based trailing stops.', json.dumps(['Trend Follow'])),
        ('trama_strategy', 'TRAMA', 'Trend Regularized Moving Average from the LuxAlgo library.', json.dumps(['LuxAlgo', 'MA'])),
        ('vwap_reversion', 'VWAP Reversion', 'Trades price deviations back to the Volume Weighted Average Price.', json.dumps(['Volume', 'Mean Reversion']))
    ]
    with get_db() as db:
        for strat in strategies:
            db.execute('''
                INSERT OR IGNORE INTO strategies (id, name, description, tags)
                VALUES (?, ?, ?, ?)
            ''', strat)
            
            db.execute('''
                INSERT OR IGNORE INTO strategy_state (strategy_id, status)
                VALUES (?, 'FLAT')
            ''', (strat[0],))

if __name__ == '__main__':
    init_db()
    seed_strategies()
    print("Database initialized successfully.")
