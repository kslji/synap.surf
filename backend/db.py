import sqlite3
import os
import json
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), 'synap.db')

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL;')
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
                email TEXT,
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
                target_pct REAL,
                stop_loss_pct REAL,
                asset_name TEXT,
                ai_engine TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(wallet_address, strategy_id)
            )
        ''')
        
        # Safe migrations for existing table
        try:
            db.execute("ALTER TABLE subscriptions ADD COLUMN target_pct REAL")
            db.execute("ALTER TABLE subscriptions ADD COLUMN stop_loss_pct REAL")
            db.execute("ALTER TABLE subscriptions ADD COLUMN asset_name TEXT")
            db.execute("ALTER TABLE subscriptions ADD COLUMN ai_engine TEXT")
        except Exception:
            pass

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

        # Nansen API Cache (to serve as context for Claude chat)
        db.execute('''
            CREATE TABLE IF NOT EXISTS nansen_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT,
                cache_key TEXT UNIQUE,
                response_json TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Claude Chat Cache — saves token burn by serving cached AI responses
        db.execute('''
            CREATE TABLE IF NOT EXISTS chat_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE,       -- SHA256(normalized_prompt + context_type)
                context_type TEXT,
                prompt TEXT,
                response TEXT,
                embedding_json TEXT,         -- JSON float array for semantic similarity search
                hit_count INTEGER DEFAULT 1, -- how many times this was served from cache
                tokens_saved INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP         -- NULL = never expires
            )
        ''')

        # AI Feedback Table (for tracking likes/dislikes on AI responses)
        db.execute('''
            CREATE TABLE IF NOT EXISTS ai_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_index INTEGER,
                feedback TEXT,
                text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Safe migrations — add columns that may not exist in older DB files
        try:
            db.execute("ALTER TABLE chat_cache ADD COLUMN embedding_json TEXT")
        except Exception:
            pass  # Column already exists, that's fine

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

        # ── NEW RELATIONAL TABLES FOR PRODUCTION ──

        # Portfolios
        db.execute('''
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT, -- Foreign key to users(wallet_address)
                portfolio_type TEXT, -- 'PAPER' or 'LIVE'
                cash REAL DEFAULT 0,
                total_equity REAL DEFAULT 0,
                unrealized_pnl REAL DEFAULT 0,
                realized_pnl REAL DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, portfolio_type)
            )
        ''')

        # Active Positions
        db.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER, -- Foreign key to portfolios(id)
                coin TEXT,
                side TEXT,
                entry_price REAL,
                current_price REAL,
                size_usd REAL,
                leverage INTEGER,
                unrealized_pnl REAL,
                unrealized_pnl_pct REAL,
                stop_loss REAL,
                take_profit_1 REAL,
                take_profit_2 REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Trade Logs
        db.execute('''
            CREATE TABLE IF NOT EXISTS trade_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT, -- Foreign key to users(wallet_address)
                event TEXT,
                coin TEXT,
                side TEXT,
                entry_price REAL,
                exit_price REAL,
                position_size_usd REAL,
                leverage INTEGER,
                stop_loss REAL,
                take_profit_1 REAL,
                take_profit_2 REAL,
                conviction REAL,
                reasoning TEXT,
                pnl_usd REAL,
                pnl_pct REAL,
                hold_duration_hours REAL,
                action TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # AI Decision Logs
        db.execute('''
            CREATE TABLE IF NOT EXISTS decision_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT, -- Can be NULL for global AI decisions
                prompt_chars INTEGER,
                response_chars INTEGER,
                decision_json TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Generic Key-Value Store for Market Data (Market Intel, Top Perps, Watchlist)
        db.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                key TEXT PRIMARY KEY,
                value_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

def seed_strategies():
    strategies = [
        ('bar_up_down', 'Bar Up Down', 'Momentum reversal logic that flips long when the current bar closes higher than its open, and the open is higher than the previous close. Extremely responsive to sudden price swings.', json.dumps(['Price Action', 'Reversal'])),
        ('bollinger_bands', 'Bollinger Bands', 'Classic mean-reversion. Buys when price pierces below the lower 2-standard-deviation band (oversold), and sells when it pushes above the upper band (overbought).', json.dumps(['Volatility', 'Mean Reversion'])),
        ('candle_2_closure', 'Candle 2 Closure', 'A robust confirmation strategy that waits for two consecutive candles to close in the same direction before executing, filtering out market noise and fake-outs.', json.dumps(['LuxAlgo', 'Confirmation'])),
        ('channel_breakout', 'Channel Breakout', 'Pure momentum breakout. It draws a dynamic Donchian channel using the 20-period highs and lows, entering trades the exact moment a new extreme is broken.', json.dumps(['Trend', 'Breakout'])),
        ('consecutive_up_down', 'Consecutive Up Down', 'Identifies micro-trends by executing a trade only after a strict sequence of 3 or more consecutive bullish/bearish candle closures.', json.dumps(['Momentum'])),
        ('delta_reaction', 'Delta Reaction Zones', 'Advanced order flow algorithm that tracks volume delta (buying vs selling pressure) combined with structural Breakout of Structure (BOS) waves to pinpoint entries.', json.dumps(['Order Flow', 'BOS'])),
        ('fib_sequence', 'Fibonacci Sequence Grid', 'Utilizes mathematical Fibonacci retracement levels (0.382, 0.618) to build a dynamic trading grid, automatically buying dips at institutional discount zones.', json.dumps(['Levels', 'BigBeluga'])),
        ('future_swing', 'Future Swing', 'A macro swing-trading model designed to catch multi-day trends. It uses higher timeframe trend-following indicators to ride massive directional moves.', json.dumps(['Trend', 'Swing'])),
        ('gold_ob_finder', 'Gold OB Finder', 'Smart Money Concepts algorithm specifically tuned to locate high-probability Institutional Order Blocks, entering limit orders on the retest.', json.dumps(['SMC', 'Order Block'])),
        ('greedy', 'Greedy Strategy', 'An aggressive high-frequency scalping model. It takes immediate, frequent profits on tiny price gaps rather than waiting for large trends to develop.', json.dumps(['Aggressive', 'Scalp'])),
        ('hyper', 'Hyper Scalper', 'Sub-minute chart trading algorithm using micro-structure momentum shifts to rapidly enter and exit positions.', json.dumps(['High Frequency'])),
        ('ichimoku_cloud', 'Ichimoku Cloud', 'Follows the Japanese Ichimoku Kinko Hyo system. Trades the Tenkan/Kijun cross but only executes if the price has successfully broken out of the Kumo (cloud).', json.dumps(['Trend', 'Complex'])),
        ('ict_smc_reversal', 'ICT SMC Reversal', 'Waits for retail traders to be trapped by a liquidity sweep (fake breakout), then enters the opposite direction during the ensuing Market Structure Shift (MSS).', json.dumps(['SMC', 'Institutional'])),
        ('impulse_trend', 'Impulse Trend Levels', 'Measures the absolute velocity of price impulses. It only takes breakout trades if the underlying speed of the candle meets proprietary BOSWave thresholds.', json.dumps(['Momentum'])),
        ('inside_bar', 'Inside Bar', 'Price action pattern that detects volatility compression (a candle completely engulfed by the previous one) and trades the explosive breakout that follows.', json.dumps(['Price Action'])),
        ('luxalgo_msb_ob', 'LuxAlgo MSB/OB Kit', 'Premium Smart Money toolkit that automatically maps internal and external Market Structure Breaks (MSB) to trade structural retracements.', json.dumps(['Premium', 'SMC'])),
        ('macd', 'MACD Cross', 'The industry standard momentum indicator. Triggers buy/sell orders precisely when the MACD histogram crosses the zero line, indicating a shift in momentum.', json.dumps(['Indicator', 'Trend'])),
        ('moving_avg_2_line', 'Moving Avg 2 Line', 'A classic dual moving average crossover. Buys when the fast EMA (9-period) crosses above the slow EMA (21-period), and sells when it crosses below.', json.dumps(['Trend'])),
        ('nadaraya_watson', 'Nadaraya Watson Envelope', 'A cutting-edge, non-repainting kernel smoothing algorithm. It fades extreme anomalies when price violently pierces its mathematical boundary.', json.dumps(['Kernel', 'Smoothing'])),
        ('parabolic_sar', 'Parabolic SAR', 'A Stop and Reverse trailing strategy. It stays continuously in the market, flipping its position whenever the Parabolic SAR dots cross the price.', json.dumps(['Reversal', 'Trend'])),
        ('predicta_futures', 'Predicta Futures v4', 'Machine-learning inspired directional model that evaluates multiple technical confluences simultaneously before predicting the next macro move.', json.dumps(['ML', 'Advanced'])),
        ('rob_booker_adx', 'Rob Booker ADX Breakout', 'Only executes volatility breakouts if the Average Directional Index (ADX) is above 25, ensuring there is enough institutional volume to sustain the trend.', json.dumps(['Trend', 'Volatility'])),
        ('rsi_strategy', 'RSI Strategy', 'Buys when the Relative Strength Index drops below 30 (oversold) and hooks back up. Sells when RSI exceeds 70 (overbought) and hooks down.', json.dumps(['Oscillator', 'OB/OS'])),
        ('saiyan_occ', 'Saiyan OCC', 'Highly aggressive momentum oscillator. It enters trades based on Open/Close moving average crossovers with tight stop losses.', json.dumps(['Momentum'])),
        ('supertrend', 'Supertrend', 'A robust trend-follower that uses Average True Range (ATR) to draw a dynamic stop-loss line. It rides trends endlessly until the trendline is broken.', json.dumps(['Trend Follow'])),
        ('trama_strategy', 'TRAMA', 'Trend Regularized Moving Average. Unlike normal MAs, TRAMA smartly flattens out during sideways chop to avoid fake-outs, only angling during true trends.', json.dumps(['LuxAlgo', 'MA'])),
        ('vwap_reversion', 'VWAP Reversion', 'Institutional algorithm that fades price deviations. When an asset moves too many standard deviations away from its VWAP, it trades the snap-back to fair value.', json.dumps(['Volume', 'Mean Reversion']))
    ]
    with get_db() as db:
        for strat in strategies:
            db.execute('''
                INSERT INTO strategies (id, name, description, tags)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET 
                    name=excluded.name,
                    description=excluded.description,
                    tags=excluded.tags
            ''', strat)
            
            db.execute('''
                INSERT OR IGNORE INTO strategy_state (strategy_id, status)
                VALUES (?, 'FLAT')
            ''', (strat[0],))


# ── ORM-Like Helper Functions (Library) ──

def get_market_data(key: str) -> dict:
    """Fetch JSON data from the generic key-value store."""
    try:
        with get_db() as db:
            row = db.execute("SELECT value_json FROM market_data WHERE key = ?", (key,)).fetchone()
            if row and row["value_json"]:
                return json.loads(row["value_json"])
    except Exception:
        pass
    return {}

def set_market_data(key: str, data: dict):
    """Save JSON data to the generic key-value store."""
    try:
        with get_db() as db:
            db.execute('''
                INSERT INTO market_data (key, value_json) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=CURRENT_TIMESTAMP
            ''', (key, json.dumps(data, default=str)))
    except Exception as e:
        print(f"Error setting market data for {key}: {e}")

def get_portfolio(user_id: str, portfolio_type: str) -> dict:
    """Fetch portfolio stats for a given user and type (PAPER/LIVE)."""
    try:
        with get_db() as db:
            row = db.execute("SELECT * FROM portfolios WHERE user_id = ? AND portfolio_type = ?", (user_id, portfolio_type)).fetchone()
            if row:
                return dict(row)
    except Exception:
        pass
    return {}

def update_portfolio(user_id: str, portfolio_type: str, updates: dict):
    """Update fields in a portfolio (e.g., cash, realized_pnl, etc.)."""
    if not updates:
        return
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values())
    values.extend([user_id, portfolio_type])
    
    try:
        with get_db() as db:
            db.execute(f'''
                UPDATE portfolios 
                SET {set_clause}, updated_at=CURRENT_TIMESTAMP
                WHERE user_id = ? AND portfolio_type = ?
            ''', tuple(values))
    except Exception as e:
        print(f"Error updating portfolio {user_id}: {e}")

def get_recent_trades(limit: int = 20, user_id: str = None) -> list:
    """Fetch recent trades, optionally filtered by user."""
    try:
        with get_db() as db:
            if user_id:
                rows = db.execute("SELECT * FROM trade_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit)).fetchall()
            else:
                rows = db.execute("SELECT * FROM trade_logs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]
    except Exception:
        return []

def log_trade(trade_data: dict):
    """Insert a new trade log."""
    columns = ', '.join(trade_data.keys())
    placeholders = ', '.join(['?'] * len(trade_data))
    values = tuple(trade_data.values())
    try:
        with get_db() as db:
            db.execute(f"INSERT INTO trade_logs ({columns}) VALUES ({placeholders})", values)
    except Exception as e:
        print(f"Error logging trade: {e}")

if __name__ == '__main__':
    init_db()
    seed_strategies()
    print("Database initialized successfully.")
