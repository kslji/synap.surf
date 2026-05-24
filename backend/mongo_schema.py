#!/usr/bin/env python3
"""
algo_brain MongoDB schema — collections, indexes, and seeds.

Usage:
  python -m backend.mongo_schema          # add/update indexes (safe, no data loss)
  python -m backend.reset_mongo_schema    # DROP ALL and rebuild (destructive)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pymongo import ASCENDING, DESCENDING, MongoClient
from backend.database import MONGO_URL

DB_NAME = "algo_brain"

# ─── Index definitions ────────────────────────────────────────────────────────
# Format: (keys_list, options_dict)
# Keys that appear in EVERY query for a collection should be the first field
# of a compound index (leftmost-prefix rule).

COLLECTIONS: dict[str, list] = {

    # ── users ──────────────────────────────────────────────────────────────────
    # Lookup is ALWAYS by wallet_address (case-insensitive regex).
    "users": [
        ([("wallet_address", ASCENDING)], {"unique": True}),
    ],

    # ── trade_logs ─────────────────────────────────────────────────────────────
    # Most queried collection. Key patterns:
    #   1. (user_id | wallet_address) + timestamp  → paginated trade history
    #   2. user_id + event + status                → open-position check, BOT trades
    #   3. user_id + hl_tid                        → dedup FILL inserts (unique)
    #   4. user_id + event + timestamp             → cleanup service
    #   5. strategy_id + coin + timestamp          → strategy-scoped analytics
    "trade_logs": [
        # Global recency scan (used by _load_all_trades without user filter)
        ([("timestamp", DESCENDING)], {}),

        # User trade history — the primary read path
        ([("user_id",       ASCENDING), ("timestamp", DESCENDING)], {}),
        ([("wallet_address", ASCENDING), ("timestamp", DESCENDING)], {}),

        # Open-position check: user + event + status
        ([("user_id",        ASCENDING),
          ("event",          ASCENDING),
          ("status",         ASCENDING),
          ("strategy_id",    ASCENDING)], {}),
        ([("wallet_address", ASCENDING),
          ("event",          ASCENDING),
          ("status",         ASCENDING),
          ("strategy_id",    ASCENDING)], {}),

        # Cleanup service: event-type filter per user
        ([("user_id", ASCENDING), ("event", ASCENDING), ("timestamp", DESCENDING)], {}),

        # FILL dedup: unique only where hl_tid is present and event is FILL
        ([("user_id", ASCENDING), ("hl_tid", ASCENDING)],
         {"unique": True,
          "partialFilterExpression": {"hl_tid": {"$type": "long"}, "event": "FILL"}}),

        # Strategy analytics: coin performance, P&L roll-ups
        ([("strategy_id", ASCENDING),
          ("coin",         ASCENDING),
          ("timestamp",    DESCENDING)], {}),

        # BOT signal tracing: find which signals were executed for a user
        ([("user_id",    ASCENDING),
          ("action",     ASCENDING),
          ("signal_id",  ASCENDING)], {"sparse": True}),
    ],

    # ── signals_queue ──────────────────────────────────────────────────────────
    # Worker polls: status=PENDING, sort timestamp ASC (FIFO).
    # Server reads: status IN [PROCESSED, PROCESSING], sort timestamp DESC.
    "signals_queue": [
        ([("status", ASCENDING), ("timestamp", ASCENDING)],  {}),   # worker poll
        ([("status", ASCENDING), ("timestamp", DESCENDING)], {}),   # server read
        ([("strategy_id", ASCENDING), ("status", ASCENDING)], {}),  # per-strategy filter
    ],

    # ── synap_surf_ai ──────────────────────────────────────────────────────────
    # Worker query: status=ACTIVE + strategy_id + asset_name  (hottest path)
    # Server query: wallet_address + strategy_id              (upsert / status)
    "synap_surf_ai": [
        # Unique subscription record per (wallet, strategy)
        ([("wallet_address", ASCENDING), ("strategy_id", ASCENDING)],
         {"unique": True}),

        # Worker subscription lookup: must cover status + strategy + asset
        ([("status",      ASCENDING),
          ("strategy_id", ASCENDING),
          ("asset_name",  ASCENDING)], {}),

        # Server status queries for a single wallet
        ([("wallet_address", ASCENDING), ("status", ASCENDING)], {}),
    ],

    # ── decision_logs ──────────────────────────────────────────────────────────
    # Inserted once per AI cycle. Read rarely (admin/debug only).
    # decision_json is a serialised string — top-level fields added in signals_queue.
    "decision_logs": [
        ([("timestamp", DESCENDING)], {}),
    ],

    # ── market_data ────────────────────────────────────────────────────────────
    # Key-value store. Every read/write is by exact key.
    "market_data": [
        ([("key", ASCENDING)], {"unique": True}),
    ],

    # ── portfolios ─────────────────────────────────────────────────────────────
    "portfolios": [
        ([("user_id", ASCENDING), ("portfolio_type", ASCENDING)],
         {"unique": True}),
    ],

    # ── runner_lock ────────────────────────────────────────────────────────────
    "runner_lock": [
        ([("_id", ASCENDING)], {}),
    ],

    # ── nansen_cache ───────────────────────────────────────────────────────────
    # TTL: auto-expire entries after 25 hours so stale data never lingers.
    "nansen_cache": [
        ([("cache_key", ASCENDING)], {"unique": True}),
        ([("timestamp", DESCENDING)], {}),
        # TTL index — MongoDB deletes docs ~1 h after `timestamp` + 25 h
        ([("timestamp", ASCENDING)], {"expireAfterSeconds": 90_000}),
    ],

    # ── chat_cache ─────────────────────────────────────────────────────────────
    # Two read patterns:
    #   1. Exact: cache_key + expires_at > now
    #   2. Semantic: context_type + expires_at > now (embedding similarity scan)
    "chat_cache": [
        ([("cache_key",    ASCENDING)], {"unique": True}),
        ([("context_type", ASCENDING), ("expires_at", DESCENDING)], {}),
        ([("created_at",   DESCENDING)], {}),
        # TTL: auto-expire after `expires_at` passes (stored as ISO string — use
        # created_at + offset instead; kept as manual field for now)
    ],

    # ── backtest_cache ─────────────────────────────────────────────────────────
    "backtest_cache": [
        ([("strategy_id", ASCENDING),
          ("timeframe",   ASCENDING),
          ("coin",        ASCENDING)],
         {"unique": True}),
    ],

    # ── strategies_metadata ────────────────────────────────────────────────────
    "strategies_metadata": [
        ([("strategy_id", ASCENDING)], {"unique": True}),
    ],

    # ── strategy_state ─────────────────────────────────────────────────────────
    "strategy_state": [
        ([("strategy_id", ASCENDING)], {"unique": True}),
    ],

    # ── ai_feedback ────────────────────────────────────────────────────────────
    "ai_feedback": [
        ([("message_index", ASCENDING)], {}),
    ],
}

# ─── Seeds ────────────────────────────────────────────────────────────────────
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


# ─── Apply (safe — no drops) ──────────────────────────────────────────────────
def apply_indexes(*, verbose: bool = True) -> None:
    """Create/update indexes on all collections without touching existing data."""
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[DB_NAME]

    for coll_name, index_specs in COLLECTIONS.items():
        coll = db[coll_name]
        for keys, opts in index_specs:
            try:
                coll.create_index(keys, **opts)
                if verbose:
                    key_str = ", ".join(f"{k}:{d}" for k, d in keys)
                    print(f"  ✓ {coll_name}  [{key_str}]  {opts or ''}")
            except Exception as e:
                # Conflicting index definition (e.g. TTL vs non-TTL on same key)
                # — drop the old one and recreate.
                if verbose:
                    print(f"  ⚠ {coll_name} index conflict ({e}) — recreating")
                try:
                    idx_name = "_".join(f"{k}_{d}" for k, d in keys)
                    coll.drop_index(idx_name)
                    coll.create_index(keys, **opts)
                    if verbose:
                        print(f"  ✓ {coll_name} recreated")
                except Exception as e2:
                    print(f"  ✗ {coll_name} failed: {e2}")

    # Seed market_data keys (idempotent)
    for key in MARKET_DATA_SEEDS:
        db.market_data.update_one(
            {"key": key},
            {"$setOnInsert": {"key": key, "value_json": "{}"}},
            upsert=True,
        )

    # Ensure runner_lock exists
    db.runner_lock.update_one(
        {"_id": "runner_lock"},
        {"$setOnInsert": {"_id": "runner_lock", "locked_until": 0}},
        upsert=True,
    )

    if verbose:
        print(f"\n✅ Indexes applied. Collections: {sorted(db.list_collection_names())}")
    client.close()


# ─── Reset (destructive) ──────────────────────────────────────────────────────
def reset_database(*, drop_all: bool = True) -> None:
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[DB_NAME]

    existing = sorted(db.list_collection_names())
    print(f"Database: {DB_NAME}  existing={existing or '(none)'}")

    if drop_all:
        for name in existing:
            db[name].drop()
            print(f"  dropped: {name}")

    for coll_name, index_specs in COLLECTIONS.items():
        coll = db[coll_name]
        for keys, opts in index_specs:
            try:
                coll.create_index(keys, **opts)
            except Exception as e:
                print(f"  ⚠ {coll_name}: {e}")
        print(f"  created: {coll_name}")

    db.runner_lock.insert_one({"_id": "runner_lock", "locked_until": 0})
    for key in MARKET_DATA_SEEDS:
        db.market_data.update_one(
            {"key": key},
            {"$setOnInsert": {"key": key, "value_json": "{}"}},
            upsert=True,
        )

    print(f"\nDone. Collections: {sorted(db.list_collection_names())}")
    client.close()


if __name__ == "__main__":
    apply_indexes()
