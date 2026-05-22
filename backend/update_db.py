import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'synap.db')
conn = sqlite3.connect(DB_PATH)

# Alter subscriptions table to add coin
try:
    conn.execute("ALTER TABLE subscriptions ADD COLUMN coin TEXT DEFAULT 'BTC'")
    print("Added coin column to subscriptions.")
except sqlite3.OperationalError:
    print("Coin column already exists in subscriptions.")

# Recreate backtest_cache to include coin in primary key
conn.execute("DROP TABLE IF EXISTS backtest_cache")
conn.execute('''
    CREATE TABLE backtest_cache (
        strategy_id TEXT,
        timeframe TEXT,
        coin TEXT,
        metrics_json TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (strategy_id, timeframe, coin)
    )
''')
conn.commit()
conn.close()
print("Recreated backtest_cache with coin in Primary Key.")
