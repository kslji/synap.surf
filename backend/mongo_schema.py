#!/usr/bin/env python3
"""
algo_brain MongoDB: drop all collections, recreate schema + indexes.

Usage (from repo root, venv active):
  python -m backend.mongo_schema
  # or: python -m backend.reset_mongo_schema
  python -m backend.populate_mongo_strategies   # optional: seed strategy metadata
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pymongo import ASCENDING, DESCENDING, MongoClient
from backend.database import MONGO_URL

DB_NAME = "algo_brain"

# Collections used by the codebase (no legacy duplicates).
COLLECTIONS: dict[str, list] = {
    "users": [
        ([("wallet_address", ASCENDING)], {"unique": True}),
    ],
    "trade_logs": [
        ([("timestamp", DESCENDING)], {}),
        ([("user_id", ASCENDING), ("timestamp", DESCENDING)], {}),
        ([("wallet_address", ASCENDING), ("timestamp", DESCENDING)], {}),
        ([("user_id", ASCENDING), ("hl_tid", ASCENDING)], {"unique": True, "sparse": True}),
        ([("strategy_id", ASCENDING), ("coin", ASCENDING), ("timestamp", DESCENDING)], {}),
    ],
    "decision_logs": [
        ([("timestamp", DESCENDING)], {}),
    ],
    "strategy_state": [
        ([("strategy_id", ASCENDING)], {"unique": True}),
    ],
    "synap_surf_ai": [
        ([("wallet_address", ASCENDING), ("strategy_id", ASCENDING)], {"unique": True}),
        ([("status", ASCENDING)], {}),
        ([("strategy_id", ASCENDING), ("status", ASCENDING)], {}),
    ],
    "market_data": [
        ([("key", ASCENDING)], {"unique": True}),
    ],
    "portfolios": [
        ([("user_id", ASCENDING), ("portfolio_type", ASCENDING)], {"unique": True}),
    ],
    "signals_queue": [
        ([("status", ASCENDING), ("timestamp", ASCENDING)], {}),
    ],
    "runner_lock": [
        ([("_id", ASCENDING)], {}),
    ],
    "nansen_cache": [
        ([("cache_key", ASCENDING)], {"unique": True}),
        ([("timestamp", DESCENDING)], {}),
    ],
    "strategies_metadata": [
        ([("strategy_id", ASCENDING)], {"unique": True}),
    ],
    "backtest_cache": [
        (
            [("strategy_id", ASCENDING), ("timeframe", ASCENDING), ("coin", ASCENDING)],
            {"unique": True},
        ),
    ],
    "chat_cache": [
        ([("cache_key", ASCENDING)], {"unique": True}),
        ([("created_at", DESCENDING)], {}),
    ],
    "ai_feedback": [
        ([("message_index", ASCENDING)], {}),
    ],
}

# Seed documents for key-value market_data (services fill values on startup).
MARKET_DATA_SEEDS = [
    "top_perps",
    "market_intelligence",
    "market_intelligence_global",
    "volatility_ticker_top_20",
    "active_watchlist",
    "user_watchlist",
    "watchlist",
    "telegram_settings",
    "live_positions",
    "nansen_credits",
]


def reset_database(*, drop_all: bool = True) -> None:
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[DB_NAME]

    existing = sorted(db.list_collection_names())
    print(f"Database: {DB_NAME}")
    print(f"Existing collections ({len(existing)}): {existing or '(none)'}")

    if drop_all:
        for name in existing:
            db[name].drop()
            print(f"  dropped: {name}")

    for coll_name, index_specs in COLLECTIONS.items():
        coll = db[coll_name]
        for keys, opts in index_specs:
            coll.create_index(keys, **opts)
        print(f"  created collection + indexes: {coll_name}")

    db.runner_lock.insert_one({"_id": "runner_lock", "locked_until": 0})
    print("  seeded: runner_lock")

    for key in MARKET_DATA_SEEDS:
        db.market_data.update_one(
            {"key": key},
            {"$setOnInsert": {"key": key, "value_json": "{}"}},
            upsert=True,
        )
    print(f"  seeded: market_data keys ({len(MARKET_DATA_SEEDS)})")

    final = sorted(db.list_collection_names())
    print(f"\nDone. Collections ({len(final)}): {final}")
    client.close()


if __name__ == "__main__":
    reset_database(drop_all=True)
