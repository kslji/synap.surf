#!/usr/bin/env python3
"""
brain/trade_journal.py — Comprehensive logging and trade journal.
Logs every trade, AI decision, and portfolio snapshot.

Output:
  - brain/logs/trades_YYYYMMDD.jsonl    — one line per trade
  - brain/logs/decisions_YYYYMMDD.jsonl — one line per AI decision
  - brain/logs/daily_summary.json       — rolling daily P&L
  - Console: rich colored output
"""

import json
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from backend.database import get_sync_db

from synap.config import LOGS_DIR

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# LOG FILE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _trades_file() -> Path:
    return LOGS_DIR / f"trades_{_today_str()}.jsonl"


def _decisions_file() -> Path:
    return LOGS_DIR / f"decisions_{_today_str()}.jsonl"


def _daily_summary_file() -> Path:
    return LOGS_DIR / "daily_summary.json"


def _append_jsonl(filepath: Path, record: dict):
    """Append a JSON record to a JSONL file."""
    try:
        with open(filepath, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as e:
        logger.error(f"Failed to write to {filepath}: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TRADE LOGGING
# ═══════════════════════════════════════════════════════════════════════════════


def log_trade_open(
    coin: str,
    side: str,        # "LONG" or "SHORT"
    entry_price: float,
    position_size_usd: float,
    leverage: int,
    stop_loss: float,
    take_profit_1: float,
    take_profit_2: float,
    conviction: float,
    reasoning: str,
):
    """Log a new trade entry."""
    try:
        db = get_sync_db()
        db.trade_logs.insert_one({
            "event": "TRADE_OPEN",
            "coin": coin,
            "side": side,
            "entry_price": round(entry_price, 6),
            "position_size_usd": round(position_size_usd, 2),
            "leverage": leverage,
            "stop_loss": round(stop_loss, 6),
            "take_profit_1": round(take_profit_1, 6),
            "take_profit_2": round(take_profit_2, 6),
            "conviction": round(conviction, 2),
            "reasoning": reasoning,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"DB Error log_trade_open: {e}")

    logger.info(
        f"\n{'='*60}\n"
        f"  🚀 TRADE OPENED: {side} {coin}\n"
        f"  Entry:      ${entry_price:.4f}\n"
        f"  Size:       ${position_size_usd:.2f} @ {leverage}x leverage\n"
        f"  Stop Loss:  ${stop_loss:.4f}\n"
        f"  TP1:        ${take_profit_1:.4f}\n"
        f"  TP2:        ${take_profit_2:.4f}\n"
        f"  Conviction: {conviction:.0%}\n"
        f"  Reason:     {reasoning}\n"
        f"{'='*60}"
    )


def log_trade_close(
    coin: str,
    side: str,
    entry_price: float,
    exit_price: float,
    position_size_usd: float,
    leverage: int,
    pnl_usd: float,
    pnl_pct: float,
    reason: str,
    hold_duration_hours: float,
    wallet_address: str = None,
):
    """Log a trade exit."""
    try:
        db = get_sync_db()
        
        # Mark any existing TRADE_OPEN logs for this coin as CLOSED
        # so UI correctly removes 'POSITION ACTIVE'
        query = {
            "coin": coin,
            "event": "TRADE_OPEN",
            "status": {"$nin": ["CLOSED", "FAILED"]}
        }
        if wallet_address:
            import re
            query["wallet_address"] = re.compile(f"^{re.escape(wallet_address)}$", re.IGNORECASE)

        db.trade_logs.update_many(
            query,
            {"$set": {"status": "CLOSED"}}
        )

        trade_doc = {
            "event": "TRADE_CLOSE",
            "coin": coin,
            "side": side,
            "entry_price": round(entry_price, 6),
            "exit_price": round(exit_price, 6),
            "position_size_usd": round(position_size_usd, 2),
            "leverage": leverage,
            "pnl_usd": round(pnl_usd, 2),
            "pnl_pct": round(pnl_pct, 2),
            "hold_duration_hours": round(hold_duration_hours, 1),
            "reasoning": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if wallet_address:
            trade_doc["wallet_address"] = wallet_address
            trade_doc["user_id"] = wallet_address

        db.trade_logs.insert_one(trade_doc)
    except Exception as e:
        logger.error(f"DB Error log_trade_close: {e}")

    emoji = "✅" if pnl_usd >= 0 else "❌"
    logger.info(
        f"\n{'='*60}\n"
        f"  {emoji} TRADE CLOSED: {side} {coin}\n"
        f"  Entry:    ${entry_price:.4f} → Exit: ${exit_price:.4f}\n"
        f"  P&L:      ${pnl_usd:+.2f} ({pnl_pct:+.2f}%)\n"
        f"  Duration: {hold_duration_hours:.1f}h\n"
        f"  Reason:   {reason}\n"
        f"{'='*60}"
    )


def log_trade_update(
    coin: str,
    action: str,
    details: str,
):
    """Log a position update (move SL, partial close, etc.)."""
    try:
        db = get_sync_db()
        db.trade_logs.insert_one({
            "event": "TRADE_UPDATE",
            "coin": coin,
            "action": action,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"DB Error log_trade_update: {e}")
    logger.info(f"  🔄 {coin}: {action} — {details}")


# ═══════════════════════════════════════════════════════════════════════════════
# AI DECISION LOGGING
# ═══════════════════════════════════════════════════════════════════════════════


def log_ai_decision(decision: dict, raw_prompt_size: int = 0, raw_response_size: int = 0):
    """Log the full AI decision for review and debugging."""
    trades = decision.get("trades", [])
    updates = decision.get("position_updates", [])
    scan = decision.get("scan_result", {})

    logger.info(f"  🧠 AI Decision: {len(trades)} new trades, {len(updates)} position updates")
    if scan.get("top_coins"):
        logger.info(f"  👀 Watching: {scan['top_coins']}")
    if scan.get("reasoning"):
        logger.info(f"  💭 {scan['reasoning'][:200]}")

    try:
        db = get_sync_db()
        res = db.decision_logs.insert_one({
            "prompt_chars": raw_prompt_size,
            "response_chars": raw_response_size,
            "decision_json": json.dumps(decision, default=str),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        return res.inserted_id
    except Exception as e:
        logger.error(f"DB Error log_ai_decision: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO SNAPSHOT
# ═══════════════════════════════════════════════════════════════════════════════


def log_portfolio_snapshot(portfolio: dict):
    """Print a beautiful portfolio snapshot to console."""
    positions = portfolio.get("positions", [])
    cash = portfolio.get("cash", 0)
    total_equity = portfolio.get("total_equity", 0)
    unrealized_pnl = portfolio.get("unrealized_pnl", 0)
    realized_pnl = portfolio.get("realized_pnl", 0)

    logger.info(
        f"\n{'─'*60}\n"
        f"  📋 PORTFOLIO SNAPSHOT\n"
        f"  Cash:            ${cash:.2f}\n"
        f"  Unrealized P&L:  ${unrealized_pnl:+.2f}\n"
        f"  Realized P&L:    ${realized_pnl:+.2f}\n"
        f"  Total Equity:    ${total_equity:.2f}\n"
        f"  Open Positions:  {len(positions)}\n"
        f"{'─'*60}"
    )

    for pos in positions:
        pnl = pos.get("unrealized_pnl", 0)
        pnl_pct = pos.get("unrealized_pnl_pct", 0)
        emoji = "🟢" if pnl >= 0 else "🔴"
        logger.info(
            f"  {emoji} {pos['side']:5s} {pos['coin']:6s} | "
            f"entry=${pos['entry_price']:.4f} | "
            f"curr=${pos.get('current_price', 0):.4f} | "
            f"P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%) | "
            f"SL=${pos.get('stop_loss', 0):.4f}"
        )

    if not positions:
        logger.info("  💤 No open positions")

    logger.info(f"{'─'*60}\n")


# ═══════════════════════════════════════════════════════════════════════════════
# DAILY SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════


def update_daily_summary(portfolio: dict):
    """Update the rolling daily summary file."""
    try:
        summary_file = _daily_summary_file()
        existing = {}
        if summary_file.exists():
            with open(summary_file) as f:
                existing = json.load(f)

        today = _today_str()
        existing[today] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_equity": round(portfolio.get("total_equity", 0), 2),
            "cash": round(portfolio.get("cash", 0), 2),
            "unrealized_pnl": round(portfolio.get("unrealized_pnl", 0), 2),
            "realized_pnl": round(portfolio.get("realized_pnl", 0), 2),
            "open_positions": len(portfolio.get("positions", [])),
            "total_trades": portfolio.get("total_trades", 0),
            "winning_trades": portfolio.get("winning_trades", 0),
            "losing_trades": portfolio.get("losing_trades", 0),
        }

        # Keep last 90 days only
        sorted_keys = sorted(existing.keys())
        if len(sorted_keys) > 90:
            for old_key in sorted_keys[:-90]:
                del existing[old_key]

        db = get_sync_db()
        db.market_data.update_one(
            {"key": "daily_summary"},
            {"$set": {
                "value_json": json.dumps(existing, default=str),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
            
    except Exception as e:
        logger.error(f"Failed to update daily summary: {e}")


def update_market_intel(sentiment: dict, decision: dict):
    """
    Update the market_intelligence.json file for the dashboard.
    Combines raw sentiment data with the AI's latest market assessment.
    """
    try:
        intel_file = LOGS_DIR / "market_intelligence.json"
        
        # Get AI view from decision
        market_view = decision.get("market_assessment", "Waiting for AI assessment...")
        if not market_view and decision.get("skip_reason"):
            market_view = f"AI Skipping: {decision['skip_reason']}"

        # Extract Fear & Greed
        fg = sentiment.get("fear_greed", {})
        
        # Extract trending narratives
        categories = sentiment.get("trending_categories") or []
        narratives = [c["name"] for c in categories[:10]]

        # Extract trending coins
        trending = sentiment.get("trending_coins") or []
        coins = [c["symbol"] for c in trending[:10]]

        intel_data = {
            "market_view": market_view,
            "fear_greed": {
                "value": fg.get("value", 50),
                "classification": fg.get("classification", "Neutral"),
                "trend": fg.get("trend_direction", "STABLE")
            },
            "trending_coins": coins,
            "trending_narratives": narratives,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        db = get_sync_db()
        db.market_data.update_one(
            {"key": "market_intelligence"},
            {"$set": {
                "value_json": json.dumps(intel_data, default=str),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
            
        logger.info("  📊 Market Intelligence updated for dashboard")

    except Exception as e:
        logger.error(f"Failed to update market intelligence: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# CSV EXPORT
# ═══════════════════════════════════════════════════════════════════════════════


def export_trades_csv(output_path: Optional[Path] = None):
    """Export all trades from JSONL files to a single CSV for analysis."""
    if output_path is None:
        output_path = LOGS_DIR / "all_trades.csv"

    all_trades = []
    try:
        db = get_sync_db()
        # Fetch all trade logs, sorted by timestamp
        rows = list(db.trade_logs.find().sort("timestamp", 1))
        # Remove MongoDB _id before exporting to CSV
        for r in rows:
            if "_id" in r:
                del r["_id"]
        all_trades = rows
    except Exception as e:
        logger.error(f"Failed to export trades to CSV: {e}")
        return

    if not all_trades:
        logger.info("No trades to export")
        return

    # Write CSV
    fieldnames = list(all_trades[0].keys())
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_trades)

    logger.info(f"📊 Exported {len(all_trades)} trade events to {output_path}")
