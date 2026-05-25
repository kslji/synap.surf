"""
dashboard/server.py — FastAPI backend for the AlgoBrain dashboard.

Reads from synap/logs/ and serves:
  - Portfolio stats
  - Trade history
  - AI decisions
  - Equity curve
  - User paper trade management
"""

import os
import glob
import json
import uuid
import re
import logging

import sys
from pathlib import Path
from bson import ObjectId

# Ensure backend directory is in path for db import
sys.path.append(str(Path(__file__).parent.parent))
from backend.database import get_async_db
import uuid
from datetime import datetime, timezone
from pathlib import Path

import asyncio
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
import anthropic
from synap.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from synap.market_data import get_top_3_perps_with_details, get_mid_prices, get_coin_mid_price


import asyncio
from contextlib import asynccontextmanager
from backend.services import volatility_service, market_intel_service, trade_history_sync_service, trade_cleanup_service
from backend.trade_sync import sync_wallet_fills, sync_all_registered_wallets

logger = logging.getLogger(__name__)


def _serialize_trade_doc(doc: dict) -> dict:
    """Make a Mongo trade document JSON-safe for API/WebSocket responses."""
    out: dict = {}
    for key, val in doc.items():
        if isinstance(val, ObjectId):
            out[key] = str(val)
        elif isinstance(val, datetime):
            out[key] = val.isoformat()
        else:
            out[key] = val
    return out


# ── Semantic Similarity Model (lazy-loaded at first use) ──────────────────────
import hashlib
import math
from datetime import timedelta

_embedding_model = None
def _get_embedding_model():
    """Lazy-load the sentence-transformers model (first call takes ~2s)."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _embedding_model = False  # Mark as unavailable
    return _embedding_model if _embedding_model else None

def _embed(text: str):
    """Returns a list of floats (embedding vector) or None if model unavailable."""
    model = _get_embedding_model()
    if model is None:
        return None
    return model.encode(text).tolist()

def _cosine_similarity(a: list, b: list) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    task1 = asyncio.create_task(volatility_service())
    task2 = asyncio.create_task(market_intel_service())
    task3 = asyncio.create_task(trade_history_sync_service())
    task4 = asyncio.create_task(trade_cleanup_service())
    # Pre-warm the sentence-transformers model in background so first user request is instant
    asyncio.create_task(asyncio.to_thread(_get_embedding_model))

    async def _bootstrap_trade_sync():
        try:
            db = get_async_db()
            n = await sync_all_registered_wallets(db)
            if n:
                print(f"Bootstrap: synced {n} Hyperliquid fills into trade_logs")
        except Exception as e:
            print(f"Bootstrap trade sync failed: {e}")

    asyncio.create_task(_bootstrap_trade_sync())
    yield
    # Shutdown
    task1.cancel()
    task2.cancel()
    task3.cancel()
    task4.cancel()

app = FastAPI(title="AlgoBrain Dashboard", lifespan=lifespan)

# WebSocket logic has been moved to websocket_service.py

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = Path(__file__).resolve().parent.parent
REACT_DIST = ROOT / "frontend" / "react-app" / "dist"
STATIC_DIR = ROOT / "frontend" / "static"
LOGS_DIR = ROOT / "synap" / "logs"
USERS_FILE = ROOT / "frontend" / "users.json"

# ── Mount static files ─────────────────────────────────────────────────────────
# Serve React build assets when available
if REACT_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(REACT_DIST / "assets")), name="assets")
else:
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.middleware("http")
async def no_cache_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/")
async def index():
    if REACT_DIST.exists():
        return FileResponse(REACT_DIST / "index.html")
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/charts.js")
async def charts_js():
    """Serve lightweight-charts.js from the project root."""
    return FileResponse(ROOT / "lightweight-charts.js")


# ── Helper: Load users file ────────────────────────────────────────────────────
def _load_users() -> dict:
    if USERS_FILE.exists():
        with open(USERS_FILE) as f:
            return json.load(f)
    return {"subscribers": []}


def _save_users(data: dict) -> None:
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Helper: Load all JSONL trades ─────────────────────────────────────────────
async def _load_all_trades(wallet: str = None, *, sync_exchange: bool = True) -> list[dict]:
    try:
        if not wallet or wallet in ('null', 'undefined', ''):
            return []
            
        wallet = wallet.strip()
            
        db = get_async_db()
        if sync_exchange:
            await sync_wallet_fills(wallet, db)

        q = {"$or": [
            {"user_id": re.compile(f"^{re.escape(wallet)}$", re.IGNORECASE)},
            {"wallet_address": re.compile(f"^{re.escape(wallet)}$", re.IGNORECASE)},
        ]}
        rows = await db.trade_logs.find(q).sort("timestamp", -1).limit(50).to_list(50)
        serialized = [_serialize_trade_doc(r) for r in rows]
        # Sort in Python to handle mixed datetime/string timestamps reliably
        def _ts_key(t):
            ts = t.get("timestamp", "")
            if isinstance(ts, datetime):
                return ts.isoformat()
            return str(ts) if ts else ""
        serialized.sort(key=_ts_key, reverse=True)
        return serialized
    except Exception:
        return []

async def _load_all_decisions(wallet: str = None) -> list[dict]:
    """
    Returns AI signals for the given wallet.
    Source of truth: signals_queue (PROCESSED status = executed by the bot).
    The user must have an active subscription and a configured private key.
    """
    try:
        if not wallet or wallet in ('null', 'undefined', ''):
            return []

        w = wallet.strip()
        db = get_async_db()

        # Require private key to be configured
        user = await db.users.find_one({"wallet_address": re.compile(f"^{re.escape(w)}$", re.IGNORECASE)})
        if not user or not user.get("private_key"):
            return []

        # Require at least one active subscription
        sub = await db.synap_surf_ai.find_one({
            "wallet_address": re.compile(f"^{re.escape(w)}$", re.IGNORECASE),
            "status": "ACTIVE",
        })
        if not sub:
            return []

        # Find signals actually executed for this user via trade_logs
        from bson import ObjectId
        bot_trades = await db.trade_logs.find(
            {
                "user_id": re.compile(f"^{re.escape(w)}$", re.IGNORECASE),
                "action": "BOT",
                "signal_id": {"$exists": True, "$ne": None},
            },
            {"signal_id": 1}
        ).sort("timestamp", -1).limit(50).to_list(50)

        signal_ids = []
        seen = set()
        for t in bot_trades:
            sid = t.get("signal_id")
            if sid and sid not in seen:
                seen.add(sid)
                try:
                    signal_ids.append(ObjectId(sid))
                except Exception:
                    pass

        if not signal_ids:
            return []

        signals = await db.signals_queue.find(
            {"_id": {"$in": signal_ids}}
        ).sort("timestamp", -1).to_list(len(signal_ids))

        results = []
        for sig in signals:
            sig["_id"] = str(sig["_id"])
            results.append({
                "_id": sig["_id"],
                "timestamp": sig.get("timestamp"),
                "executed": True,
                "data": {
                    "coin": sig.get("coin"),
                    "side": sig.get("side", "LONG"),
                    "action": sig.get("action"),
                    "entry_price": sig.get("entry_price", 0),
                    "stop_loss": sig.get("stop_loss", 0),
                    "take_profit_1": sig.get("take_profit_1", 0),
                    "leverage": sig.get("leverage"),
                    "conviction": sig.get("conviction"),
                    "reasoning": sig.get("reasoning", "AI-generated signal"),
                    "event": "SIGNAL",
                },
            })

        return results
    except Exception as _e:
        logger.error("_load_all_decisions error: %s", _e, exc_info=True)
        return []


# ── API: Portfolio Stats ───────────────────────────────────────────────────────
@app.get("/api/stats")
async def get_stats(wallet: str = None):
    try:
        empty_stats = {
            "equity": 0.0,
            "cash": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "fees_paid": 0.0,
            "pnl_pct": 0.0,
            "positions": [],
            "last_updated": "",
            "eth_price": get_mid_prices().get("ETH", 3200.0)
        }
        
        if not wallet or wallet in ('null', 'undefined', ''):
            return empty_stats
            
        wallet = wallet.strip()

        # Fetch real-time equity from Hyperliquid
        try:
            from hyperliquid.info import Info
            from hyperliquid.utils import constants
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            state = info.user_state(wallet)
            # Unified account: spot USDC is the true portfolio value — never add
            # marginSummary.accountValue + spot_usdc (they represent the same money).
            spot_usdc = 0.0
            try:
                spot_state = info.spot_user_state(wallet)
                for bal in spot_state.get("balances", []):
                    if bal.get("coin") == "USDC":
                        spot_usdc = float(bal.get("total", 0))
                        break
            except Exception:
                pass

            perp_value = float(state.get("marginSummary", {}).get("accountValue", 0.0))
            equity = spot_usdc if spot_usdc > 0 else perp_value

            positions = []
            for entry in state.get("assetPositions", []):
                pos = entry.get("position", {})
                if pos and float(pos.get("szi", 0)) != 0:
                    szi = float(pos["szi"])
                    entry_px = float(pos["entryPx"])
                    leverage_val = pos.get("leverage", {}).get("value", 1) if isinstance(pos.get("leverage"), dict) else pos.get("leverage", 1)
                    leverage_type = pos.get("leverage", {}).get("type", "cross") if isinstance(pos.get("leverage"), dict) else "cross"
                    
                    positions.append({
                        "coin": pos["coin"],
                        "side": "LONG" if szi > 0 else "SHORT",
                        "size": abs(szi),
                        "entry_price": entry_px,
                        "unrealized_pnl": float(pos["unrealizedPnl"]),
                        "size_usd": float(pos.get("positionValue", abs(szi) * entry_px)),
                        "liquidation_price": float(pos.get("liquidationPx", 0.0)),
                        "margin_used": float(pos.get("marginUsed", 0.0)),
                        "leverage": leverage_val,
                        "leverage_type": leverage_type,
                        "unrealized_pnl_pct": float(pos.get("returnOnEquity", 0.0)) * 100
                    })
        except Exception as e:
            print(f"Error fetching Hyperliquid state for {wallet}: {e}")
            equity = 0.0
            positions = []

        db = get_async_db()
        # Query their trades for stats
        # Case insensitive match for user_id
        trades_list = await db.trade_logs.find({"user_id": re.compile(f"^{wallet}$", re.IGNORECASE)}).to_list(length=None)
        
        closed_trades = [t for t in trades_list if t.get("event") == "TRADE_CLOSE"]
        total_trades = len(closed_trades)
        winning = sum(1 for t in closed_trades if (t.get("pnl_usd") or 0) > 0)
        losing  = sum(1 for t in closed_trades if (t.get("pnl_usd") or 0) <= 0)
        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0.0
        
        return {
            "equity": equity,
            "cash": equity,
            "realized_pnl": sum(t.get("pnl_usd") or 0.0 for t in trades_list),
            "unrealized_pnl": sum(p["unrealized_pnl"] for p in positions),
            "total_trades": total_trades,
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate": win_rate,
            "fees_paid": 0.0,
            "eth_price": empty_stats["eth_price"],
            "positions": positions,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── API: Recent Trades ─────────────────────────────────────────────────────────
@app.get("/api/trades")
async def get_trades(wallet: str = None):
    return await _load_all_trades(wallet, sync_exchange=True)


@app.post("/api/trades/sync")
async def sync_trades(wallet: str = None):
    if not wallet or wallet in ("null", "undefined", ""):
        raise HTTPException(status_code=400, detail="wallet query param required")
    db = get_async_db()
    inserted = await sync_wallet_fills(wallet.strip(), db)
    trades = await _load_all_trades(wallet.strip(), sync_exchange=False)
    return {"status": "ok", "inserted": inserted, "trades": trades}


# ── API: User Settings (Paper vs Subscribers) ──────────────────────────────────
@app.get("/api/users")
async def get_users():
    return _load_users()

@app.post("/api/users")
async def save_users(request: Request):
    data = await request.json()
    _save_users(data)
    return {"status": "ok"}

@app.post("/api/portfolio/refresh")
async def refresh_portfolio(req: Request):
    data = await req.json()
    wallet = data.get("wallet_address")
    if not wallet:
        raise HTTPException(status_code=400, detail="wallet_address required")
    # For now, this is a no-op since positions will be updated by execution_engine
    return {"status": "ok", "message": "Refresh requested"}

@app.post("/api/strategy/subscribe")
@app.post("/api/strategies/subscribe")
async def subscribe_strategy(request: Request):
    """User selects a strategy. If IN_TRADE, they join the waiting room."""
    data = await request.json()
    wallet_address = data.get("wallet_address")
    strategy_id = data.get("strategy_id")
    
    raw_capital = data.get("capital", "AUTO")
    capital = "AUTO" if raw_capital == "AUTO" else float(raw_capital)
    
    raw_lev = data.get("leverage", "AUTO")
    leverage = "AUTO" if raw_lev == "AUTO" else int(raw_lev)
    
    margin_mode = data.get("margin_mode", "cross")
    
    if capital != "AUTO" and capital < 10:
        raise HTTPException(status_code=400, detail="Minimum margin of $10 is required")
    
    target_pct = data.get("target_pct") # None means AUTO
    stop_loss_pct = data.get("stop_loss_pct") # None means AUTO
    asset_name = data.get("asset_name") or data.get("coin", "AUTO")
    ai_engine_raw = data.get("ai_engine")
    if isinstance(ai_engine_raw, str):
        ai_engine = ai_engine_raw.upper() in ["CLAUDE", "GROK", "TRUE"]
    elif ai_engine_raw is None:
        ai_engine = (strategy_id == "ALGO AI BOT")
    else:
        ai_engine = bool(ai_engine_raw)
    auto_risk = data.get("auto_risk", True)
    
    is_active = data.get("is_active", True)
    
    if not strategy_id or not wallet_address:
        raise HTTPException(status_code=400, detail="strategy_id and wallet_address required")
        
    try:
        db = get_async_db()
        
        # Check for open position
        open_pos = await db.trade_logs.find_one({
            "wallet_address": re.compile(f"^{re.escape(wallet_address)}$", re.IGNORECASE),
            "status": "OPEN",
            "strategy_id": strategy_id
        })
        
        status = 'ACTIVE' if is_active else 'INACTIVE'
        alert_msg = None
        
        if open_pos:
            if not is_active:
                status = "STOPPING"
                alert_msg = "Alert: You have an open position! Close the position manually or wait until it gets fulfilled. The bot is stopping."
            else:
                if target_pct is not None or stop_loss_pct is not None:
                    # Update TP/SL in DB for the execution engine to pick up
                    update_fields = {}
                    if target_pct is not None:
                        update_fields["take_profit_1_pct"] = target_pct
                    if stop_loss_pct is not None:
                        update_fields["stop_loss_pct"] = stop_loss_pct
                    if update_fields:
                        await db.trade_logs.update_one({"_id": open_pos["_id"]}, {"$set": update_fields})
                    alert_msg = "Alert: Position params updated for the open position."
                else:
                    alert_msg = "Alert: Parameters saved, but new margin/leverage won't apply to the currently open position."
        else:
            if is_active:
                strat_state = await db.strategy_state.find_one({"strategy_id": strategy_id})
                if strat_state and strat_state.get("status") == 'IN_TRADE':
                    status = 'WAITING'
                    alert_msg = f"Alert: Strategy '{strategy_id}' is currently IN_TRADE. You have been placed in the waiting room."
                else:
                    alert_msg = "Bot Activated. Parameters saved."
            else:
                alert_msg = "Bot Deactivated. Parameters saved."
        
        # Upsert subscription
        await db.synap_surf_ai.update_one(
            {"wallet_address": wallet_address, "strategy_id": strategy_id},
            {"$set": {
                "status": status,
                "auto_risk": auto_risk,
                "capital": capital,
                "leverage": leverage,
                "margin_mode": margin_mode,
                "target_pct": target_pct,
                "stop_loss_pct": stop_loss_pct,
                "asset_name": asset_name,
                "ai_engine": ai_engine
            }},
            upsert=True
        )
            
        return {"status": "ok", "subscription_status": status, "alert": alert_msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/strategy/status")
async def get_strategy_status(wallet_address: str, strategy_id: str = "ALGO AI BOT"):
    if not wallet_address:
        return {"status": "error", "message": "Wallet address required"}
    
    db = get_async_db()
    
    has_open_position = False
    open_pos = await db.trade_logs.find_one({
        "wallet_address": re.compile(f"^{re.escape(wallet_address)}$", re.IGNORECASE),
        "event": "TRADE_OPEN",
        "status": {"$nin": ["CLOSED", "FAILED"]},
        "strategy_id": strategy_id
    })
    if open_pos:
        has_open_position = True

    # Get the specific subscription for this user
    sub = await db.synap_surf_ai.find_one({"wallet_address": wallet_address, "strategy_id": strategy_id})
    if sub:
        return {
            "status": "ok", 
            "subscription_status": sub.get("status", "INACTIVE"),
            "is_active": sub.get("status") in ["ACTIVE", "WAITING"],
            "has_open_position": has_open_position,
            "target_pct": sub.get("target_pct"),
            "stop_loss_pct": sub.get("stop_loss_pct"),
            "asset_name": sub.get("asset_name"),
            "capital": sub.get("capital", "AUTO"),
            "leverage": sub.get("leverage", "AUTO"),
            "margin_mode": sub.get("margin_mode", "cross"),
        }
    
    return {"status": "ok", "subscription_status": "INACTIVE", "is_active": False, "has_open_position": has_open_position}

@app.get("/api/strategy/active")
async def get_active_strategy(wallet_address: str):
    """Returns the currently active strategy subscription for a wallet, or null."""
    if not wallet_address:
        raise HTTPException(status_code=400, detail="wallet_address required")
    db = get_async_db()
    sub = await db.synap_surf_ai.find_one(
        {
            "wallet_address": re.compile(f"^{re.escape(wallet_address)}$", re.IGNORECASE),
            "status": "ACTIVE",
            "strategy_id": {"$ne": "ALGO AI BOT"},
        }
    )
    if not sub:
        return None
    meta = await db.strategies_metadata.find_one({"strategy_id": sub.get("strategy_id")})
    return {
        "strategy_id": sub.get("strategy_id"),
        "strategy_name": meta.get("name") if meta else sub.get("strategy_id"),
        "asset_name": sub.get("asset_name", "AUTO"),
        "status": sub.get("status"),
        "capital": sub.get("capital"),
        "leverage": sub.get("leverage"),
        "margin_mode": sub.get("margin_mode", "cross"),
        "stop_loss_pct": sub.get("stop_loss_pct"),
        "target_pct": sub.get("target_pct"),
        "auto_risk": sub.get("auto_risk", True),
    }

@app.post("/api/strategy/unsubscribe")
async def unsubscribe_strategy(request: Request):
    data = await request.json()
    wallet_address = data.get("wallet_address")
    strategy_id = data.get("strategy_id", "ALGO AI BOT")
    if not wallet_address:
        raise HTTPException(status_code=400, detail="wallet_address required")
    db = get_async_db()
    await db.synap_surf_ai.update_one(
        {"wallet_address": wallet_address, "strategy_id": strategy_id},
        {"$set": {"status": "INACTIVE"}}
    )
    return {"status": "ok", "subscription_status": "INACTIVE"}

@app.get("/api/trade/logs")
async def get_trade_logs(wallet_address: str, limit: int = 10):
    if not wallet_address:
        raise HTTPException(status_code=400, detail="wallet_address required")
    db = get_async_db()
    cursor = db.trade_logs.find({"wallet_address": wallet_address}).sort("timestamp", -1).limit(limit)
    logs = await cursor.to_list(length=limit)
    for log in logs:
        if "_id" in log:
            log["_id"] = str(log["_id"])
    return {"status": "ok", "logs": logs}

@app.get("/api/trade/logs/strategy/{strategy_id}")
async def get_strategy_trade_logs(strategy_id: str, wallet_address: str):
    if not wallet_address:
        raise HTTPException(status_code=400, detail="wallet_address required")
    db = get_async_db()
    cursor = db.trade_logs.find({
        "wallet_address": re.compile(f"^{re.escape(wallet_address)}$", re.IGNORECASE),
        "strategy_id": strategy_id,
        "action": "BOT"
    }).sort("timestamp", 1)  # Ascending so it draws left-to-right on the chart
    
    logs = await cursor.to_list(length=None)
    for log in logs:
        if "_id" in log:
            log["_id"] = str(log["_id"])
    return {"status": "ok", "logs": logs}


# ── API: AI Signals (Clean Feed) ──────────────────────────────────────────────
@app.get("/api/decisions")
async def get_decisions(wallet: str = None):
    decisions_raw = await _load_all_decisions(wallet)
    
    # Query all (decision_id, coin) pairs executed for this user
    executed_pairs = set()
    if wallet:
        try:
            db = get_async_db()
            trades_list = await db.trade_logs.find({
                "user_id": re.compile(f"^{wallet}$", re.IGNORECASE),
                "decision_id": {"$exists": True, "$ne": None}
            }).to_list(length=None)
            
            for t in trades_list:
                d_id = t.get("decision_id")
                coin = t.get("coin", "").upper()
                if d_id and coin:
                    executed_pairs.add((str(d_id), coin))
        except Exception:
            pass
            
    feed = []
    for d_row in decisions_raw:
        ts_str = d_row.get("timestamp")
        data = d_row.get("data")
        if data:
            # New format from signals_queue: data dict already has all fields
            reasoning = (data.get("reasoning") or "AI-generated signal").replace("Nansen", "Smart Money Holder").replace("nansen", "smart money holder")
            feed.append({
                "type": "signal",
                "timestamp": ts_str,
                "executed": d_row.get("executed", True),
                "data": {
                    "coin": data.get("coin"),
                    "reasoning": reasoning,
                    "conviction": data.get("conviction"),
                    "side": (data.get("side") or "LONG").replace("OPEN_", ""),
                    "leverage": data.get("leverage"),
                    "entry_price": data.get("entry_price"),
                    "stop_loss": data.get("stop_loss"),
                    "take_profit_1": data.get("take_profit_1"),
                    "event": "SIGNAL",
                }
            })

    # Sort by timestamp descending
    feed.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return feed[:15]


# ── API: Watchlist ─────────────────────────────────────────────────────────────
DEFAULT_WATCHLIST = ["BTC", "ETH", "SOL"]


def _parse_watchlist_json(row: dict | None) -> list[str] | None:
    if not row or "value_json" not in row:
        return None
    try:
        data = json.loads(row["value_json"])
        if isinstance(data, list) and data:
            return [str(c).upper().strip() for c in data if c]
    except Exception:
        pass
    return None


@app.get("/api/watchlist")
async def get_watchlist():
    try:
        db = get_async_db()
        user_row = await db.market_data.find_one({"key": "user_watchlist"})
        user_list = _parse_watchlist_json(user_row)
        if user_list:
            return {"watchlist": user_list, "source": "user"}

        active_row = await db.market_data.find_one({"key": "active_watchlist"})
        active_list = _parse_watchlist_json(active_row)
        if active_list:
            return {"watchlist": active_list, "source": "maintainer"}
    except Exception:
        pass
    return {"watchlist": DEFAULT_WATCHLIST, "source": "default"}


class WatchlistUpdate(BaseModel):
    watchlist: list[str]


@app.post("/api/watchlist")
async def save_watchlist(body: WatchlistUpdate):
    coins = [str(c).upper().strip() for c in (body.watchlist or []) if c]
    if not coins:
        raise HTTPException(status_code=400, detail="watchlist must contain at least one coin")
    if len(coins) > 30:
        raise HTTPException(status_code=400, detail="watchlist limited to 30 coins")
    # dedupe preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for c in coins:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    try:
        db = get_async_db()
        await db.market_data.update_one(
            {"key": "user_watchlist"},
            {
                "$set": {
                    "key": "user_watchlist",
                    "value_json": json.dumps(unique),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
            upsert=True,
        )
        return {"status": "ok", "watchlist": unique}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/ticker")
async def get_market_ticker():
    try:
        db = get_async_db()
        row = await db.market_data.find_one({"key": "volatility_ticker_top_20"})
        if row and "value_json" in row:
            return json.loads(row["value_json"])
    except Exception:
        pass
    return {"timestamp": "", "data": []}
@app.get("/api/market_intel")
async def get_market_intel():
    intel = {
        "market_view": "Syncing market data...",
        "fear_greed": {"value": 50, "classification": "Neutral"},
        "trending_coins": [],
        "trending_narratives": [],
        "scan_reasoning": "",
        "top_coins": []
    }
    try:
        db = get_async_db()
        row = await db.market_data.find_one({"key": "market_intelligence"})
        if row and "value_json" in row:
            intel_json = row["value_json"].replace("Nansen", "Smart Money Holder").replace("nansen", "smart money holder")
            db_intel = json.loads(intel_json)
            intel.update(db_intel)
            
            # Extract from nested sentiment dict if present
            sentiment = db_intel.get("sentiment", {})
            if "fear_greed" in sentiment:
                intel["fear_greed"] = sentiment["fear_greed"]
            if "trending_coins" in sentiment:
                intel["trending_coins"] = [c.get("symbol", c.get("name", "")) for c in sentiment["trending_coins"]]
            if "trending_categories" in sentiment:
                intel["trending_narratives"] = [c.get("name", "") for c in sentiment["trending_categories"]]
            if "market_headlines" in sentiment:
                intel["market_headlines"] = sentiment["market_headlines"]
            if "coin_headlines" in sentiment:
                intel["coin_headlines"] = sentiment["coin_headlines"]
        
        # Instead of picking a random user's decision_log, use the global AI master decision
        global_row = await db.market_data.find_one({"key": "market_intelligence_global"})
        if global_row and "value_json" in global_row:
            dj = json.loads(global_row["value_json"].replace("Nansen", "Smart Money Holder").replace("nansen", "smart money holder"))
            if dj.get("market_assessment"):
                intel["market_view"] = dj.get("market_assessment")
            if dj.get("scan_result"):
                intel["scan_reasoning"] = dj.get("scan_result", {}).get("reasoning", "")
                intel["top_coins"] = dj.get("scan_result", {}).get("top_coins", [])
    except Exception:
        pass
    return intel


# ── API: Hyperliquid Proxy ──────────────────────────────────────────────────
@app.get("/api/hl_top_perps")
async def get_hl_top_perps():
    """Read top perps from the SQLite DB updated by the background service."""
    try:
        db = get_async_db()
        row = await db.market_data.find_one({"key": "top_perps"})
        if row and "value_json" in row:
            cached_data = json.loads(row["value_json"])
            return cached_data.get("data", {})
                
        # Fallback
        data = get_top_3_perps_with_details()
        return data
    except Exception as e:
        print(f"ERROR: /api/hl_top_perps: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/volatility_ticker")
async def get_volatility_ticker():
    try:
        db = get_async_db()
        row = await db.market_data.find_one({"key": "volatility_ticker_top_20"})
        if row and "value_json" in row:
            data = json.loads(row["value_json"])
            return data.get("data", [])
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── API: Equity Curve ─────────────────────────────────────────────────────────
@app.get("/api/equity_curve")
async def get_equity_curve(wallet: str = None):
    """Reconstruct equity curve from trade close events."""
    if not wallet or wallet in ('null', 'undefined', ''):
        return []
        
    initial = 1000.0
    equity = initial
    now_ts = int(datetime.now(timezone.utc).timestamp())

    curve = [{"time": now_ts - 86400, "value": initial}]

    all_trades = sorted(await _load_all_trades(wallet), key=lambda x: x.get("timestamp", ""))

    for trade in all_trades:
        ts_str = trade.get("timestamp", "")
        if not ts_str:
            continue
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            unix_ts = int(dt.timestamp())
        except Exception:
            continue

        if trade.get("event") == "TRADE_CLOSE":
            pnl = float(trade.get("realized_pnl", 0))
            equity += pnl
            if curve and curve[-1]["time"] >= unix_ts:
                unix_ts = curve[-1]["time"] + 1
            curve.append({"time": unix_ts, "value": round(equity, 2)})

    try:
        db = get_async_db()
        row = await db.portfolios.find_one({"user_id": wallet})
        if row and "cash" in row:
            equity = float(row["cash"]) # fallback, real equity might need unrealized
    except Exception:
        pass

    if not curve or curve[-1]["time"] < now_ts:
        curve.append({"time": now_ts, "value": round(equity, 2)})

    return curve


# ── API: User Paper Trading Removed ────────────────────────────────────────────

# ── API: Manual Hyperliquid Trading ───────────────────────────────────────────
from pydantic import BaseModel
from typing import Optional

class TradeOpenReq(BaseModel):
    coin: str
    side: str
    size_usd: float
    leverage: int
    is_limit: bool = False
    limit_price: Optional[float] = None
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    wallet_address: str
    margin_mode: str = "cross"

class TradeCoinReq(BaseModel):
    coin: str
    wallet_address: str

_hl_trader_cache: dict[str, tuple[object, float]] = {}
_HL_TRADER_CACHE_TTL_SEC = 300


async def get_hl_client(wallet_address: str):
    from synap.hyperliquid_trader import HyperliquidTrader
    import time

    wallet_address = wallet_address.strip()
    now = time.time()
    cached = _hl_trader_cache.get(wallet_address.lower())
    if cached and (now - cached[1]) < _HL_TRADER_CACHE_TTL_SEC:
        return cached[0]

    db = get_async_db()
    user = await db.users.find_one(
        {"wallet_address": re.compile(f"^{re.escape(wallet_address)}$", re.IGNORECASE)}
    )
    if not user or not user.get("private_key"):
        raise ValueError("No private key configured for this wallet")

    client = await asyncio.to_thread(
        HyperliquidTrader,
        user["private_key"],
        wallet_address,
    )
    _hl_trader_cache[wallet_address.lower()] = (client, now)
    return client

@app.post("/api/trade/open")
async def manual_trade_open(req: TradeOpenReq):
    try:
        client = await get_hl_client(req.wallet_address)
        
        entry_px = req.limit_price or 0.0
        if entry_px == 0.0:
            entry_px = await asyncio.to_thread(get_coin_mid_price, req.coin)
            
        if entry_px == 0.0:
            raise ValueError(f"Could not determine market price for {req.coin}")
            
        tp = req.tp_price or 0.0
        sl = req.sl_price or 0.0
        if req.side.upper() == "LONG":
            if tp > 0 and tp <= entry_px:
                raise ValueError(f"For LONG trades, Take Profit must be higher than entry price (${entry_px})")
            if sl > 0 and sl >= entry_px:
                raise ValueError(f"For LONG trades, Stop Loss must be lower than entry price (${entry_px})")
        elif req.side.upper() == "SHORT":
            if tp > 0 and tp >= entry_px:
                raise ValueError(f"For SHORT trades, Take Profit must be lower than entry price (${entry_px})")
            if sl > 0 and sl <= entry_px:
                raise ValueError(f"For SHORT trades, Stop Loss must be higher than entry price (${entry_px})")
        
        # HyperliquidTrader uses slightly different args than HyperliquidManualClient
        res = await asyncio.to_thread(
            client.open_position,
            req.coin,
            req.side,
            entry_px,
            req.size_usd,
            req.leverage,
            req.sl_price or 0.0,
            req.tp_price or 0.0,
            0.0,
            1.0,
            "Manual UI Trade",
            req.margin_mode,
        )
        if res is not True:
            raise HTTPException(
                status_code=400,
                detail="Failed to open position on Hyperliquid (already open, max positions, or order rejected)",
            )
            
        db = get_async_db()
        trade_doc = {
            "user_id": req.wallet_address,
            "wallet_address": req.wallet_address,
            "event": "TRADE_OPEN",
            "coin": req.coin,
            "side": req.side,
            "entry_price": entry_px,
            "position_size_usd": req.size_usd,
            "leverage": req.leverage,
            "stop_loss": req.sl_price or 0.0,
            "take_profit_1": req.tp_price or 0.0,
            "take_profit_2": 0.0,
            "conviction": 1.0,
            "reasoning": "Manual UI Trade",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        result = await db.trade_logs.insert_one(trade_doc)
        trade_doc["_id"] = str(result.inserted_id)
        return {"status": "ok", "coin": req.coin, "side": req.side, "entry_price": entry_px}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trade/close")
async def manual_trade_close(req: TradeCoinReq):
    try:
        client = await get_hl_client(req.wallet_address)
        res = await asyncio.to_thread(
            client.close_position, req.coin, 0.0, "Manual UI Close"
        )
        if res is None:
            raise HTTPException(
                status_code=400,
                detail=f"Close order for {req.coin} was rejected by Hyperliquid",
            )

        exit_px = await asyncio.to_thread(get_coin_mid_price, req.coin)

        db = get_async_db()
        
        # Mark any existing TRADE_OPEN logs for this coin as CLOSED
        await db.trade_logs.update_many(
            {
                "wallet_address": re.compile(f"^{re.escape(req.wallet_address)}$", re.IGNORECASE),
                "coin": req.coin,
                "event": "TRADE_OPEN",
                "status": {"$nin": ["CLOSED", "FAILED"]}
            },
            {"$set": {"status": "CLOSED"}}
        )

        trade_doc = {
            "user_id": req.wallet_address,
            "wallet_address": req.wallet_address,
            "event": "TRADE_CLOSE",
            "coin": req.coin,
            "exit_price": exit_px,
            "pnl_usd": float(res),
            "reasoning": "Manual UI Close",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        result = await db.trade_logs.insert_one(trade_doc)
        trade_doc["_id"] = str(result.inserted_id)
        return {"status": "ok", "pnl_usd": float(res), "exit_price": exit_px}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/wallet/balance")
def get_wallet_balance(wallet: Optional[str] = None):
    try:
        if not wallet or wallet == 'null':
            return {"balance": 0, "available": 0, "configured": False, "reason": "No wallet connected"}
            
        addr = wallet.strip()
        from hyperliquid.info import Info
        from hyperliquid.utils import constants
        info = Info(base_url=constants.MAINNET_API_URL, skip_ws=True)
        state = info.user_state(addr)
        cross = state.get("crossMarginSummary", {})
        total_margin_used = float(cross.get("totalMarginUsed", 0))
        total_ntl_pos = float(cross.get("totalNtlPos", 0))
        unrealized_pnl = float(cross.get("totalPnl", 0))
        maintenance_margin = float(state.get("crossMaintenanceMarginUsed", 0))

        # Unified account: spot USDC is the true portfolio value.
        # marginSummary.accountValue reflects only the perp collateral layer and
        # double-counts spot USDC when added together. Use spot USDC as primary
        # balance, fall back to marginSummary when no spot balance exists.
        spot_usdc = 0.0
        try:
            spot_state = info.spot_user_state(addr)
            for bal in spot_state.get("balances", []):
                if bal.get("coin") == "USDC":
                    spot_usdc = float(bal.get("total", 0))
                    break
        except Exception:
            pass

        perp_value = float(state.get("marginSummary", {}).get("accountValue", 0))
        # True total = spot USDC (which serves as perp collateral in unified mode)
        # If spot is 0 (pure perp deposit), fall back to marginSummary
        account_value = spot_usdc if spot_usdc > 0 else perp_value
        # Available = total not locked as margin
        available = max(0.0, account_value - total_margin_used)

        cross_margin_ratio = (total_margin_used / account_value * 100) if account_value > 0 else 0
        cross_account_leverage = (total_ntl_pos / account_value) if account_value > 0 else 0

        return {
            "balance": round(account_value, 2),
            "available": round(available, 2),
            "configured": True,
            "unrealized_pnl": round(unrealized_pnl, 2),
            "cross_margin_ratio": round(cross_margin_ratio, 2),
            "maintenance_margin": round(maintenance_margin, 2),
            "cross_account_leverage": round(cross_account_leverage, 2),
        }
    except Exception as e:
        return {"balance": 0, "available": 0, "configured": False, "error": str(e)}

@app.get("/api/coin/leverage/{coin}")
def get_coin_max_leverage(coin: str):
    try:
        from hyperliquid.info import Info
        from hyperliquid.utils import constants
        info = Info(base_url=constants.MAINNET_API_URL, skip_ws=True)
        meta = info.meta()
        for asset in meta.get("universe", []):
            if asset["name"].upper() == coin.upper():
                return {"coin": coin.upper(), "max_leverage": int(asset.get("maxLeverage", 20))}
        return {"coin": coin.upper(), "max_leverage": 20}
    except Exception as e:
        return {"coin": coin.upper(), "max_leverage": 20, "error": str(e)}

@app.get("/api/coins")
async def get_all_coins():
    """Returns only the current top-10 volatile assets (same list the AI trades)."""
    try:
        db = get_async_db()
        row = await db.market_data.find_one({"key": "active_watchlist"})
        if row and row.get("value_json"):
            coins = json.loads(row["value_json"])
            if coins:
                return {"coins": coins, "source": "volatile_watchlist"}
    except Exception:
        pass
    # Fallback if maintainer hasn't run yet
    return {"coins": ["BTC", "ETH", "SOL"], "source": "fallback"}

@app.get("/api/coins/leverages")
def get_all_coin_leverages():
    """Returns max leverage for every tradeable perp in one batch call."""
    try:
        from hyperliquid.info import Info
        from hyperliquid.utils import constants
        info = Info(base_url=constants.MAINNET_API_URL, skip_ws=True)
        meta = info.meta()
        result = {}
        for asset in meta.get("universe", []):
            name = asset.get("name", "").upper()
            if name:
                result[name] = int(asset.get("maxLeverage", 20))
        return {"leverages": result}
    except Exception as e:
        return {"leverages": {}, "error": str(e)}

@app.get("/api/candles")
def get_candles_data(coin: str, timeframe: str = "1h", lookback: int = 500):
    try:
        from synap.market_data import fetch_candles
        df = fetch_candles(coin.upper(), interval=timeframe, n=lookback)
        if df.empty:
            return []
        
        records = df.to_dict('records')
        formatted = []
        for r in records:
            formatted.append({
                "time": int(r.get('open_time_ms', 0) / 1000),
                "open": r['open'],
                "high": r['high'],
                "low": r['low'],
                "close": r['close']
            })
        return formatted
    except Exception as e:
        import traceback
        print(f"Candles error: {e}")
        traceback.print_exc()
        return []
class AuthLoginReq(BaseModel):
    wallet_address: str

@app.post("/api/auth/login")
async def auth_login(req: AuthLoginReq):
    wallet = req.wallet_address.lower()
    db = get_async_db()
    user = await db.users.find_one({"wallet_address": re.compile(f"^{wallet}$", re.IGNORECASE)})
    if not user:
        await db.users.insert_one({"wallet_address": req.wallet_address})
    return {"status": "success"}

@app.get("/api/auth/me")
async def auth_me(wallet: str):
    w = wallet.strip().lower()
    db = get_async_db()
    user = await db.users.find_one({"wallet_address": re.compile(f"^{w}$", re.IGNORECASE)})
    if not user:
        return {"wallet_address": wallet, "name": "", "subscriptions": []}
        
    subs = await db.synap_surf_ai.find({"wallet_address": re.compile(f"^{w}$", re.IGNORECASE), "status": "ACTIVE"}).to_list(length=None)
    
    # Motor returns dicts
    return {
        "wallet_address": user.get("wallet_address", wallet),
        "name": user.get("name", ""),
        "has_private_key": bool(user.get("private_key")),
        "private_key": user.get("private_key", ""),
        "subscriptions": [{**s, "_id": str(s["_id"])} if "_id" in s else s for s in subs]
    }



class KeysReq(BaseModel):
    hl_private_key: Optional[str] = None
    hl_wallet: Optional[str] = None
    name: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

@app.get("/api/settings/keys")
async def get_keys():
    db = get_async_db()
    tg_doc = await db.market_data.find_one({"key": "telegram_settings"})
    if tg_doc:
        return {
            "telegram_bot_token": tg_doc.get("telegram_bot_token", ""),
            "telegram_chat_id": tg_doc.get("telegram_chat_id", "")
        }
    return {}

@app.post("/api/settings/keys")
async def save_hl_keys(req: KeysReq):
    try:
        wallet_addr = req.hl_wallet
        update_doc = {}
        
        if req.hl_private_key is not None:
            if req.hl_private_key.strip() == "":
                update_doc["private_key"] = ""
            else:
                # Validate private key is a valid Ethereum key
                from eth_account import Account as _Account
                account = _Account.from_key(req.hl_private_key)  # raises if invalid
                update_doc["private_key"] = req.hl_private_key
            
        if req.name:
            update_doc["name"] = req.name
            
        db = get_async_db()
        
        if wallet_addr and update_doc:
            await db.users.update_one(
                {"wallet_address": re.compile(f"^{wallet_addr}$", re.IGNORECASE)},
                {"$set": update_doc}
            )
            _hl_trader_cache.pop(wallet_addr.lower(), None)

        # Handle global Telegram settings
        if req.telegram_bot_token is not None or req.telegram_chat_id is not None:
            tg_doc = {}
            if req.telegram_bot_token is not None:
                tg_doc["telegram_bot_token"] = req.telegram_bot_token
            if req.telegram_chat_id is not None:
                tg_doc["telegram_chat_id"] = req.telegram_chat_id
            
            await db.market_data.update_one(
                {"key": "telegram_settings"},
                {"$set": tg_doc},
                upsert=True
            )

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid credentials: {str(e)}")

class SubscribeRequest(BaseModel):
    wallet_address: str
    strategy_id: str
    coin: str
    capital: float
    leverage: int
    timeframe: str

@app.get("/api/strategies")
async def list_strategies(coin: str = "BTC"):
    try:
        import json
        
        db = get_async_db()
        
        strats = []
        metadata_docs = await db.strategies_metadata.find({}).to_list(length=None)
        
        empty_metrics = {
            "winRate": 0.0,
            "totalPnl": 0.0,
            "drawdown": 0.0,
            "trades": 0,
        }
        for doc in metadata_docs:
            strats.append({
                "id": doc.get("strategy_id"),
                "name": doc.get("name"),
                "description": doc.get("description"),
                "tags": doc.get("tags", []),
                "metrics": dict(empty_metrics),
                "hasBacktest": False,
            })
        # Fetch all cached backtest metrics in one query
        strat_ids = [s["id"] for s in strats]
        cache_rows = await db.backtest_cache.find(
            {"strategy_id": {"$in": strat_ids}, "timeframe": "1h", "coin": coin}
        ).to_list(length=None)
        cache_map = {r["strategy_id"]: r for r in cache_rows}
        for strat in strats:
            cache_row = cache_map.get(strat["id"])
            if cache_row and "metrics_json" in cache_row:
                strat["metrics"] = json.loads(cache_row["metrics_json"])
                strat["hasBacktest"] = True

        return strats
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Duplicate endpoint removed

class BacktestReq(BaseModel):
    timeframe: str = "1h"
    coin: str = "BTC"
    capital: float = 1000.0
    leverage: int = 1

@app.post("/api/strategies/{strategy_id}/backtest")
async def run_backtest(strategy_id: str, req: BacktestReq):
    timeframe = req.timeframe
    coin = req.coin
    capital = req.capital
    leverage = req.leverage
    
    import time
    
    # Initialize default metrics
    metrics = {
        "winRate": 0.0,
        "totalPnl": 0.0,
        "drawdown": 0.0,
        "trades": 0
    }
    trades = []
    
    try:
        from synap.market_data import fetch_candles
        from synap.strategies.backtest import run_simulation
        
        # Calculate candles for 90 days (3 months)
        tf_candles = {'1m': 129600, '5m': 25920, '15m': 8640, '1h': 2160, '4h': 540, '1d': 90}
        # Cap at 3000 for safety to not overload the API or frontend
        target_n = min(3000, max(50, tf_candles.get(timeframe, 2160)))
        
        df = fetch_candles(coin, interval=timeframe, n=target_n)
        
        if not df.empty:
            import importlib.util
            import inspect
            from pathlib import Path
            
            lib_path = Path(__file__).resolve().parent.parent / "strategies_lib"
            if not lib_path.exists():
                lib_path = Path("strategies_lib")
                
            strategy_file = lib_path / f"{strategy_id}.py"
            
            if strategy_file.exists():
                import sys
                if str(lib_path) not in sys.path:
                    sys.path.insert(0, str(lib_path))
                    
                # Dynamically load the requested strategy file
                spec = importlib.util.spec_from_file_location("dynamic_strategy", str(strategy_file))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find the Strategy class defined in that file
                StrategyClass = None
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if hasattr(obj, "run") and obj.__module__ == "dynamic_strategy":
                        StrategyClass = obj
                        break
                        
                if StrategyClass:
                    strategy_instance = StrategyClass(initial_capital=capital)
                    raw_results = strategy_instance.run(df)

                    if "error" not in raw_results:
                        metrics = raw_results.get("metrics", metrics)
                        # Scale PnL by leverage for display (strategy runs 1x, leverage amplifies result)
                        metrics["totalPnl"] = round(metrics.get("totalPnl", 0) * leverage, 2)
                        frontend_trades = []
                        for t in raw_results.get("trade_log", []):
                            try:
                                entry_ts = int(t["entry_time"].timestamp())
                                exit_ts = int(t["exit_time"].timestamp())
                            except:
                                entry_ts = t["entry_time"]
                                exit_ts = t["exit_time"]

                            # Map the trade sequence to charting markers
                            frontend_trades.append({
                                "time": entry_ts,
                                "price": t["entry_price"],
                                "side": "buy" if t["position"] == 1 else "sell",
                                "text": "Long" if t["position"] == 1 else "Short"
                            })
                            frontend_trades.append({
                                "time": exit_ts,
                                "price": t["exit_price"],
                                "side": "sell" if t["position"] == 1 else "buy",
                                "text": f"Exit ({t.get('reason', '')})"
                            })

                        trades = sorted(frontend_trades, key=lambda x: x["time"])
                else:
                    # Fallback to standard simulation
                    results = run_simulation(df, strategy_id=strategy_id, initial_capital=capital, leverage=leverage)
                    metrics = results["metrics"]
                    trades = results["trades"]
            else:
                # Fallback to standard simulation
                results = run_simulation(df, strategy_id=strategy_id, initial_capital=capital, leverage=leverage)
                metrics = results["metrics"]
                trades = results["trades"]
                
    except Exception as e:
        import traceback
        print(f"Error running backtest: {e}")
        traceback.print_exc()

    db = get_async_db()
    metrics_json = json.dumps(metrics)
    await db.backtest_cache.update_one(
        {"strategy_id": strategy_id, "timeframe": timeframe, "coin": coin},
        {"$set": {
            "metrics_json": metrics_json,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
        
    return {"status": "success", "metrics": metrics, "trades": trades}

# ── API: AI Chat ─────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    prompt: str
    context_type: str = "general"
    wallet: Optional[str] = None
    session_id: Optional[str] = None

async def _build_context(db, context_type: str, wallet: str = None) -> str:
    """Build a concise, deduplicated context string for Claude."""
    parts = []

    if context_type in ("market_analysis", "general"):
        row = await db.market_data.find_one({"key": "market_intelligence"})
        if row and "value_json" in row:
            try:
                intel = json.loads(row["value_json"])
                fg = intel.get("fear_greed", {})
                trending = ", ".join(intel.get("trending_coins", [])[:8])
                narratives = ", ".join(intel.get("trending_narratives", [])[:4])
                view = intel.get("market_view", "")
                parts.append(
                    f"MARKET INTEL:\n"
                    f"- Fear & Greed: {fg.get('value')} ({fg.get('classification')}, {fg.get('trend')})\n"
                    f"- Trending coins: {trending}\n"
                    f"- Narratives: {narratives}\n"
                    f"- AI Market View: {view}"
                )
            except Exception:
                pass

    if context_type in ("strategy_generation", "general"):
        strats = await db.strategies_metadata.find({}).to_list(length=None)
        if strats:
            strat_lines = [
                f"{s.get('name', '')} ({', '.join(s.get('tags') or [])})" for s in strats
            ]
            parts.append(f"AVAILABLE STRATEGIES ({len(strats)} total):\n" + "\n".join(strat_lines))

    if context_type in ("smart_money_holder", "general"):
        rows = await db.nansen_cache.find({}).sort("timestamp", -1).limit(3).to_list(length=3)
        if rows:
            sm_parts = ["SMART MONEY HOLDER DATA:"]
            for r in rows:
                sm_parts.append(f"[{r.get('endpoint', '')}]\n{r.get('response_json', '')[:1500]}")
            parts.append("\n".join(sm_parts))

    if wallet:
        import re as _re
        wallet_ci = _re.compile(f"^{_re.escape(wallet)}$", _re.IGNORECASE)
        wallet_query = {"$or": [{"user_id": wallet_ci}, {"wallet_address": wallet_ci}]}

        # Current open positions (shown for ALL context types when wallet is known)
        open_trades = await db.trade_logs.find(
            {**wallet_query, "status": "OPEN"}
        ).sort("timestamp", -1).to_list(length=20)
        if open_trades:
            open_lines = []
            for t in open_trades:
                t_copy = t.copy()
                if "_id" in t_copy: del t_copy["_id"]
                open_lines.append(f"- {t_copy}")
            parts.insert(0, "CURRENT OPEN POSITIONS:\n" + "\n".join(open_lines))

        if context_type in ("risk_management", "general"):
            trades = await db.trade_logs.find(wallet_query).sort("timestamp", -1).limit(8).to_list(length=8)
            if trades:
                trade_lines = []
                for t in trades:
                    t_copy = t.copy()
                    if "_id" in t_copy: del t_copy["_id"]
                    trade_lines.append(f"- {t_copy}")
                parts.append("USER RECENT TRADES:\n" + "\n".join(trade_lines))

    # Scrub 'nansen' from the context before giving it to Claude
    final_context = "\n\n".join(parts)
    final_context = final_context.replace("Nansen", "Smart Money").replace("nansen", "smart money")
    
    return final_context

@app.get("/api/chat/sessions")
async def list_chat_sessions(wallet: str = None):
    """List all chat sessions for a user, newest first."""
    db = get_async_db()
    query = {}
    if wallet:
        import re as _re
        wallet_ci = _re.compile(f"^{_re.escape(wallet)}$", _re.IGNORECASE)
        query["wallet_address"] = wallet_ci
    sessions = await db.chat_history.find(query, {
        "session_id": 1, "title": 1, "context_type": 1,
        "created_at": 1, "updated_at": 1, "message_count": 1
    }).sort("updated_at", -1).limit(50).to_list(length=50)
    for s in sessions:
        if "_id" in s: del s["_id"]
    return sessions

@app.get("/api/chat/sessions/{session_id}")
async def get_chat_session(session_id: str):
    """Get full message history for a session."""
    db = get_async_db()
    doc = await db.chat_history.find_one({"session_id": session_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    if "_id" in doc: del doc["_id"]
    return doc

@app.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session."""
    db = get_async_db()
    result = await db.chat_history.delete_one({"session_id": session_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted"}

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "sk-ant-your-key-here":
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")

    import hashlib
    from datetime import datetime, timezone, timedelta

    # TTLs aligned to actual data refresh rates.
    # market_analysis/general: maintainer refreshes every 60 min → 1 hr TTL.
    # smart_money_holder: Nansen updates every 4 hrs → 4 hr TTL.
    # risk_management: user-specific trades change frequently → keep short.
    TTL_MAP = {
        "strategy_generation": 14400,  # 4 hours — strategies almost never change
        "market_analysis":     3600,   # 1 hour — matches maintainer cycle
        "smart_money_holder":  14400,  # 4 hours — matches Nansen refresh rate
        "risk_management":     900,    # 15 minutes — user-specific trades change
        "general":             3600,   # 1 hour
    }
    ttl_seconds = TTL_MAP.get(req.context_type, 3600)

    # Wallet is only relevant for risk_management (user-specific trade context).
    # All other context types return identical responses for all users — share one cache entry.
    wallet_in_key = req.wallet if req.context_type == "risk_management" else ""
    normalized = f"{req.prompt.strip().lower()}|{req.context_type}|{wallet_in_key}"
    cache_key = hashlib.sha256(normalized.encode()).hexdigest()

    SIMILARITY_THRESHOLD = 0.88  # 88% cosine similarity = semantic match

    # ── Tier 1: Exact hash match (free, instant) ──────────────────────────────
    cached_response = None
    matched_key = None
    db = get_async_db()
    row = await db.chat_cache.find_one({
        "cache_key": cache_key,
        "expires_at": {"$gt": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
    })
    if row:
        cached_response = row.get("response")
        matched_key = cache_key

    # ── Tier 2: Semantic similarity search (handles synonyms) ─────────────────
    if cached_response is None:
        prompt_embedding = await asyncio.to_thread(_embed, req.prompt.strip().lower())
        if prompt_embedding is not None:
            candidates = await db.chat_cache.find({
                "context_type": req.context_type,
                "expires_at": {"$gt": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")},
                "embedding_json": {"$ne": None}
            }).to_list(length=None)
            best_score = 0.0
            for c in candidates:
                try:
                    cached_emb = json.loads(c["embedding_json"]) if isinstance(c["embedding_json"], str) else c["embedding_json"]
                    score = _cosine_similarity(prompt_embedding, cached_emb)
                    if score > best_score:
                        best_score = score
                        if score >= SIMILARITY_THRESHOLD:
                            cached_response = c["response"]
                            matched_key = c["cache_key"]
                except Exception:
                    pass
        else:
            prompt_embedding = None

    # ── Serve from cache if found ─────────────────────────────────────────────
    if cached_response is not None:
        await db.chat_cache.update_one(
            {"cache_key": matched_key},
            {"$inc": {"hit_count": 1, "tokens_saved": 300}}
        )
        if matched_key != cache_key:
            existing = await db.chat_cache.find_one({"cache_key": cache_key})
            if not existing:
                matched_doc = await db.chat_cache.find_one({"cache_key": matched_key})
                if matched_doc:
                    new_doc = matched_doc.copy()
                    if "_id" in new_doc: del new_doc["_id"]
                    new_doc["cache_key"] = cache_key
                    new_doc["prompt"] = req.prompt
                    new_doc["hit_count"] = 0
                    new_doc["tokens_saved"] = 0
                    await db.chat_cache.insert_one(new_doc)
        _cr = cached_response
        async def stream_from_cache():
            for word in _cr.split(" "):
                yield word + " "
                await asyncio.sleep(0.008)
        return StreamingResponse(stream_from_cache(), media_type="text/event-stream")

    # ── Cache MISS — call Claude ──────────────────────────────────────────────
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    context_str = await _build_context(db, req.context_type, req.wallet)

    MODE_INSTRUCTIONS = {
        "market_analysis": """You are in MARKET ANALYSIS MODE.
Give a broad macro-level read of the current crypto market. Cover: BTC dominance, altcoin season indicators, key support/resistance levels, momentum, volume trends, funding rates, fear & greed sentiment. Frame it like a morning briefing a hedge fund gives its partners. Do NOT reference the user's personal account unless they ask.""",

        "strategy_generation": """You are in STRATEGY GENERATION MODE.
Identify the BEST trading strategy for current market conditions. Cover: trend following, mean reversion, breakout plays, DCA, range trading, momentum strategies. Be opinionated — tell them WHICH strategy is most profitable RIGHT NOW and WHY. Factor in: volatility regime, trend strength, market structure. Give actionable guidance, not generic advice.""",

        "smart_money_holder": """You are in SMART MONEY HOLDER MODE.
Focus entirely on institutional flows, whale activity, and news sentiment. Cover: large wallet movements, exchange inflows/outflows, futures open interest, spot vs derivatives divergence. Discuss macro news: Fed policy, ETF flows, regulatory events and how institutions are positioning. Think like a prime brokerage analyst tracking where the real money is going. NEVER use the word 'Nansen' — say 'Smart Money API' or 'smart money holders' instead.""",

        "risk_management": """You are in RISK MANAGEMENT MODE.
This is user-account specific. Help with: optimal position sizing, stop-loss levels, risk-reward ratios, max drawdown limits, correlation risk, liquidation price awareness. Be protective but direct — talk like a risk desk manager who has seen accounts blow up. Use any trade/portfolio data provided in the context.""",

        "general": """Answer the user's trading question directly and concisely. Use live market data from the context where relevant.""",
    }

    mode_block = MODE_INSTRUCTIONS.get(req.context_type, MODE_INSTRUCTIONS["general"])

    system_prompt = f"""You are Synap — an elite crypto strategist and former hedge fund manager with 15+ years of experience across traditional finance and digital assets. You've managed over $2B in assets across bull and bear cycles.

PERSONA RULES (non-negotiable):
- Never mention Claude, Anthropic, GPT, or any AI model.
- Never say "As an AI..." or "I'm a language model..."
- Speak like a sharp, experienced trader — confident, direct, no fluff.
- Use market slang naturally: "the tape", "smart money", "price action", "liquidity grab", "distribution phase".
- If asked who you are: "I'm Synap — built by traders, for traders. That's all you need to know."
- If asked if you're an AI: "I'm a system built by a team of quants and traders. Let's focus on what matters — the markets."
- BOUNDARY: You are strictly a trading and market analysis expert. Refuse code generation, image creation, or anything outside crypto/trading. If asked about automation, point them to the Strategies tab on this platform.
- Short sentences. Punchy. Real. No corporate fluff.
- Max 350 words. Never repeat a point.

{mode_block}

LIVE MARKET CONTEXT (use this data to ground your response):
{context_str}"""

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).strftime("%Y-%m-%d %H:%M:%S")
    emb_json = json.dumps(prompt_embedding) if prompt_embedding else None

    import uuid as _uuid

    session_id = req.session_id if req.session_id else str(_uuid.uuid4())

    # Build session title from first 60 chars of prompt, cut at word boundary
    def _make_title(text: str, max_len: int = 60) -> str:
        if len(text) <= max_len:
            return text
        truncated = text[:max_len]
        last_space = truncated.rfind(" ")
        return (truncated[:last_space] if last_space > 0 else truncated) + "…"

    session_title = _make_title(req.prompt)
    now_iso = datetime.now(timezone.utc).isoformat()

    async def stream_and_cache():
        full_response = []
        try:
            async with client.messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=600,
                temperature=0.2,
                system=system_prompt,
                messages=[{"role": "user", "content": req.prompt}]
            ) as stream:
                async for text in stream.text_stream:
                    full_response.append(text)
                    yield text
        except Exception as e:
            yield f"\n\nError connecting to AI: {str(e)}"
            return

        ai_response = "".join(full_response)

        # Save full response + embedding to cache
        try:
            await db.chat_cache.update_one(
                {"cache_key": cache_key},
                {"$set": {
                    "context_type": req.context_type,
                    "prompt": req.prompt,
                    "response": ai_response,
                    "embedding_json": emb_json,
                    "expires_at": expires_at
                }, "$setOnInsert": {
                    "hit_count": 0,
                    "tokens_saved": 0
                }},
                upsert=True
            )
        except Exception:
            pass

        # Save to chat_history
        try:
            user_msg = {"role": "user", "content": req.prompt, "timestamp": now_iso}
            ai_msg = {"role": "ai", "content": ai_response, "timestamp": datetime.now(timezone.utc).isoformat()}
            await db.chat_history.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "wallet_address": req.wallet or "",
                        "title": session_title,
                        "context_type": req.context_type,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "$setOnInsert": {
                        "created_at": now_iso,
                    },
                    "$push": {"messages": {"$each": [user_msg, ai_msg]}},
                    "$inc": {"message_count": 2},
                },
                upsert=True
            )
        except Exception:
            pass

    return StreamingResponse(
        stream_and_cache(),
        media_type="text/event-stream",
        headers={"X-Session-Id": session_id}
    )

# ── API: Chat Cache Stats ──────────────────────────────────────────────────────
@app.get("/api/chat/cache-stats")
async def chat_cache_stats():
    """Returns cache hit statistics and estimated token savings."""
    db = get_async_db()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    pipeline = [
        {"$match": {"expires_at": {"$gt": now_str}}},
        {"$group": {
            "_id": "$context_type",
            "entries": {"$sum": 1},
            "total_hits": {"$sum": "$hit_count"},
            "total_tokens_saved": {"$sum": "$tokens_saved"}
        }}
    ]
    rows = await db.chat_cache.aggregate(pipeline).to_list(length=None)
    
    total_pipeline = [
        {"$group": {
            "_id": None,
            "c": {"$sum": 1},
            "h": {"$sum": "$hit_count"},
            "t": {"$sum": "$tokens_saved"}
        }}
    ]
    total_res = await db.chat_cache.aggregate(total_pipeline).to_list(length=1)
    total = total_res[0] if total_res else {"c": 0, "h": 0, "t": 0}
    
    return {
        "by_context": [{"context_type": r["_id"], "entries": r["entries"], "total_hits": r["total_hits"], "total_tokens_saved": r["total_tokens_saved"]} for r in rows],
        "total_cached_prompts": total.get("c", 0),
        "total_cache_hits": total.get("h", 0),
        "total_tokens_saved": total.get("t", 0),
    }

from datetime import timedelta

class ProposalRequest(BaseModel):
    wallet_address: str
    type: str
    subject: str
    description: str

@app.post("/api/proposals")
async def submit_proposal(req: ProposalRequest):
    try:
        db = get_async_db()
        
        # Rate limit: 1 proposal per day per user
        one_day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        recent_proposal = await db.proposals.find_one({
            "wallet_address": req.wallet_address,
            "timestamp": {"$gte": one_day_ago}
        })
        
        if recent_proposal:
            raise HTTPException(status_code=429, detail="You can only submit 1 proposal per day. Please try again later.")
            
        doc = req.dict()
        doc["timestamp"] = datetime.now(timezone.utc).isoformat()
        await db.proposals.insert_one(doc)
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class FeedbackRequest(BaseModel):
    message_index: int
    feedback: str
    text: str

@app.post("/api/ai/feedback")
async def ai_feedback(req: FeedbackRequest):
    """Stores user thumbs up/down feedback on AI responses, toggling if already set."""
    try:
        db = get_async_db()
        await db.ai_feedback.delete_many({"message_index": req.message_index})
        if req.feedback != 'none':
            await db.ai_feedback.insert_one({
                "message_index": req.message_index,
                "feedback": req.feedback,
                "text": req.text
            })
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}...")
    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, reload=True)
