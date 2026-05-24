"""Sync Hyperliquid user fills into MongoDB trade_logs."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger("backend.trade_sync")

MAX_FILLS_PER_SYNC = 200


def _parse_fill_side(fill_dir: str) -> str:
    d = fill_dir or ""
    if "Long" in d:
        return "LONG"
    if "Short" in d:
        return "SHORT"
    return d.upper() if d else "LONG"


def _fill_to_doc(wallet: str, fill: dict) -> dict:
    fill_dir = fill.get("dir", "")
    is_close = "Close" in fill_dir
    px = float(fill.get("px", 0))
    sz = float(fill.get("sz", 0))
    pnl = float(fill.get("closedPnl", 0) or 0)
    ts_ms = fill.get("time", 0)
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

    return {
        "user_id": wallet,
        "wallet_address": wallet,
        "event": "FILL",
        "coin": fill.get("coin", ""),
        "side": _parse_fill_side(fill_dir),
        "entry_price": px,
        "exit_price": px if is_close else None,
        "pnl_usd": pnl if is_close else None,
        "position_size_usd": sz * px,
        "action": "MANUAL_OR_EXTERNAL_TRADE",
        "details": fill_dir,
        "timestamp": dt.isoformat(),
        "hl_tid": fill.get("tid"),
        "hl_hash": fill.get("hash"),
        "status": "FILLED",
    }


async def sync_wallet_fills(wallet: str, db, *, info=None) -> int:
    """
    Pull recent Hyperliquid fills for ``wallet`` into ``trade_logs``.
    Returns number of newly inserted rows.
    """
    if not wallet or not wallet.startswith("0x") or len(wallet) != 42:
        return 0

    wallet = wallet.strip()
    inserted = 0

    try:
        if info is None:
            from hyperliquid.info import Info
            from hyperliquid.utils import constants

            info = Info(constants.MAINNET_API_URL, skip_ws=True)

        fills = await asyncio.to_thread(info.user_fills, wallet)
        if not fills:
            return 0

        fills = sorted(fills, key=lambda f: f.get("time", 0), reverse=True)[:MAX_FILLS_PER_SYNC]

        for fill in fills:
            tid = fill.get("tid")
            if tid is not None:
                existing = await db.trade_logs.find_one(
                    {
                        "user_id": re.compile(f"^{re.escape(wallet)}$", re.IGNORECASE),
                        "hl_tid": tid,
                    }
                )
            else:
                dt = datetime.fromtimestamp(fill.get("time", 0) / 1000, tz=timezone.utc)
                existing = await db.trade_logs.find_one(
                    {
                        "user_id": wallet,
                        "coin": fill.get("coin"),
                        "event": "FILL",
                        "side": _parse_fill_side(fill.get("dir", "")),
                        "timestamp": dt.isoformat(),
                    }
                )

            if existing:
                continue

            doc = _fill_to_doc(wallet, fill)
            await db.trade_logs.insert_one(doc)
            inserted += 1

        if inserted:
            logger.info("Synced %s new fills for %s", inserted, wallet[:10])
    except Exception as e:
        logger.error("sync_wallet_fills failed for %s: %s", wallet[:10], e)

    return inserted


async def sync_all_registered_wallets(db, *, info=None) -> int:
    rows = await db.users.find({}).to_list(length=None)
    wallets = [r.get("wallet_address") for r in rows if r.get("wallet_address")]
    total = 0
    for wallet in wallets:
        total += await sync_wallet_fills(wallet, db, info=info)
    return total
