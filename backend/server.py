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
import sqlite3
import sys
from pathlib import Path

# Ensure backend directory is in path for db import
sys.path.append(str(Path(__file__).parent.parent))
from backend.db import get_db
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
import anthropic
from synap.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from synap.market_data import get_top_3_perps_with_details, get_mid_prices
from synap.config import HL_WALLET

import asyncio
from contextlib import asynccontextmanager
from backend.services import volatility_service, market_intel_service, trade_history_sync_service

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
    # Pre-warm the sentence-transformers model in background so first user request is instant
    asyncio.create_task(asyncio.to_thread(_get_embedding_model))
    yield
    # Shutdown
    task1.cancel()
    task2.cancel()
    task3.cancel()

app = FastAPI(title="AlgoBrain Dashboard", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = Path("/Users/arjunsingh/Desktop/algo_brain")
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
    return {"subscribers": [], "paper_traders": {}}


def _save_users(data: dict) -> None:
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Helper: Load all JSONL trades ─────────────────────────────────────────────
def _load_all_trades() -> list[dict]:
    try:
        with get_db() as db:
            rows = db.execute("SELECT * FROM trade_logs ORDER BY timestamp ASC").fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []

def _load_all_decisions() -> list[dict]:
    try:
        with get_db() as db:
            rows = db.execute("SELECT * FROM decision_logs ORDER BY timestamp DESC").fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


# ── API: Portfolio Stats ───────────────────────────────────────────────────────
@app.get("/api/stats")
def get_stats():
    try:
        with get_db() as db:
            if HL_WALLET:
                row = db.execute("SELECT * FROM portfolios WHERE user_id = ? AND portfolio_type = 'LIVE'", (HL_WALLET,)).fetchone()
            else:
                row = db.execute("SELECT * FROM portfolios WHERE portfolio_type = 'LIVE' ORDER BY ROWID DESC LIMIT 1").fetchone()
                
            kv_row = db.execute("SELECT value_json FROM market_data WHERE key = 'live_positions'").fetchone()

            if not row and HL_WALLET:
                from synap.telegram_bot import get_live_hl_portfolio
                live_data = get_live_hl_portfolio()
                if live_data:
                    # Calculate percentage based on current open trades if no history exists
                    live_equity = float(live_data["total_equity"])
                    live_unrealized = float(live_data["unrealized_pnl"])
                    base_cap = live_equity - live_unrealized
                    calc_pct = round((live_unrealized / base_cap) * 100, 2) if base_cap > 0 else 0.0

                    return {
                        "equity": round(live_equity, 2),
                        "cash": round(live_data["cash"], 2),
                        "realized_pnl": round(live_data.get("last_20_realized_pnl", 0.0), 2),
                        "unrealized_pnl": round(live_unrealized, 2),
                        "total_trades": 0,
                        "winning_trades": 0,
                        "losing_trades": 0,
                        "win_rate": round(live_data.get("last_20_win_rate", 0.0), 1),
                        "fees_paid": round(live_data["cumulative_fees"], 2),
                        "pnl_pct": calc_pct,
                        "positions": live_data["positions"],
                        "last_updated": live_data["fetched_at"],
                        "is_last_20": True
                    }

            if not row:
                return {
                    "equity": 1000.0,
                    "cash": 1000.0,
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
                }
            
            positions = json.loads(kv_row["value_json"]) if kv_row else []
            
            initial_capital = 1000.0 # Base reference for paper. Live uses its own equity tracking.
            unrealized = sum(float(p.get("unrealized_pnl", 0)) for p in positions)
            
            total_trades = row["total_trades"]
            winning_trades = row["winning_trades"]
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            realized_pnl = row["realized_pnl"]

            if HL_WALLET:
                # Override DB tracking with actual live Hyperliquid history for last 20 trades
                from synap.telegram_bot import get_live_hl_portfolio
                live_data = get_live_hl_portfolio()
                if live_data:
                    equity = float(live_data["total_equity"])
                    unrealized = float(live_data["unrealized_pnl"])
                    positions = live_data["positions"]
                    realized_pnl = live_data.get("last_20_realized_pnl", 0.0)
                    win_rate = live_data.get("last_20_win_rate", 0.0)
                else:
                    equity = float(row["total_equity"])
            else:
                # Paper trades dynamically sum cash + unrealized
                equity = float(row["cash"]) + unrealized
            pnl_pct = round((equity - initial_capital) / initial_capital * 100, 2)
            if HL_WALLET:
                prev_equity = float(row["total_equity"]) if row else 0.0
                if prev_equity > 0:
                    pnl_pct = round(((equity - prev_equity) / prev_equity) * 100, 2)
                else:
                    # If we have no database history, calculate the percentage based on current open trades
                    base_capital = equity - unrealized
                    if base_capital > 0:
                        pnl_pct = round((unrealized / base_capital) * 100, 2)
                    else:
                        pnl_pct = 0.0
            
            eth_price = get_mid_prices().get("ETH", 3200.0)
            
            return {
                "equity": round(equity, 2),
                "cash": round(row["cash"], 2),
                "realized_pnl": round(realized_pnl, 2),
                "unrealized_pnl": round(unrealized, 2),
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": row["losing_trades"],
                "win_rate": round(win_rate, 1),
                "fees_paid": 0.0,
                "pnl_pct": pnl_pct,
                "eth_price": eth_price,
                "positions": positions,
                "last_updated": row["updated_at"],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── API: Recent Trades ─────────────────────────────────────────────────────────
@app.get("/api/trades")
async def get_trades():
    trades = _load_all_trades()
    return list(reversed(trades))[:20]


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
def refresh_portfolio():
    """Forces a refresh of the live portfolio state directly from Hyperliquid API."""
    if not HL_WALLET:
        raise HTTPException(status_code=400, detail="No live wallet configured.")
    try:
        from synap.hyperliquid_trader import HyperliquidTrader
        # Instantiating the trader automatically fetches state or we can call fetch directly.
        # But trader._save_state() needs an active Info call. Actually get_live_hl_portfolio() is better.
        from synap.telegram_bot import get_live_hl_portfolio
        from backend.db import get_db, set_market_data
        
        live_data = get_live_hl_portfolio()
        if live_data:
            with get_db() as db:
                db.execute('''
                    INSERT INTO portfolios (user_id, portfolio_type, cash, total_equity, unrealized_pnl, updated_at)
                    VALUES (?, 'LIVE', ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, portfolio_type) DO UPDATE SET
                        cash=excluded.cash,
                        total_equity=excluded.total_equity,
                        unrealized_pnl=excluded.unrealized_pnl,
                        updated_at=CURRENT_TIMESTAMP
                ''', (HL_WALLET, live_data["cash"], live_data["total_equity"], live_data["unrealized_pnl"]))
                
            set_market_data("live_positions", live_data["positions"])
        return {"status": "ok", "message": "Portfolio synced from Hyperliquid"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/strategy/subscribe")
async def subscribe_strategy(request: Request):
    """User selects a strategy. If IN_TRADE, they join the waiting room."""
    data = await request.json()
    wallet_address = data.get("wallet_address", HL_WALLET)
    strategy_id = data.get("strategy_id")
    capital = data.get("capital", 100)
    leverage = data.get("leverage", 10)
    timeframe = data.get("timeframe", "1h")
    
    if not strategy_id:
        raise HTTPException(status_code=400, detail="strategy_id required")
        
    try:
        with get_db() as db:
            # Check strategy state
            strat_state = db.execute("SELECT status FROM strategy_state WHERE strategy_id = ?", (strategy_id,)).fetchone()
            status = 'ACTIVE'
            alert_msg = None
            
            if strat_state and strat_state["status"] == 'IN_TRADE':
                status = 'WAITING'
                alert_msg = f"Alert: Strategy '{strategy_id}' is currently IN_TRADE. You have been placed in the waiting room and will be joined automatically when the current cycle finishes."
            
            # Upsert subscription
            db.execute('''
                INSERT INTO subscriptions (wallet_address, strategy_id, status, capital, leverage, timeframe)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(wallet_address, strategy_id) DO UPDATE SET
                    status=excluded.status,
                    capital=excluded.capital,
                    leverage=excluded.leverage,
                    timeframe=excluded.timeframe
            ''', (wallet_address, strategy_id, status, capital, leverage, timeframe))
            
        return {"status": "ok", "subscription_status": status, "alert": alert_msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── API: AI Signals (Clean Feed) ──────────────────────────────────────────────
@app.get("/api/decisions")
async def get_decisions():
    trades = _load_all_trades()
    decisions_raw = _load_all_decisions()
    
    feed = []
    for t in trades:
        # Hide raw manual FILL events from the AI Signals feed
        if t.get("event") == "FILL":
            continue
        feed.append({"type": "trade_event", "timestamp": t.get("timestamp"), "data": t})
        
    for d_row in decisions_raw:
        ts = d_row.get("timestamp")
        dj = d_row.get("decision_json")
        if dj:
            try:
                dec_obj = json.loads(dj)
                for rec_trade in dec_obj.get("trades", []):
                    signal_data = {
                        "coin": rec_trade.get("coin"),
                        "reasoning": rec_trade.get("reasoning", "").replace("Nansen", "Smart Money Holder").replace("nansen", "smart money holder"),
                        "conviction": rec_trade.get("conviction"),
                        "side": rec_trade.get("action", "LONG").replace("OPEN_", ""),
                        "leverage": rec_trade.get("leverage"),
                        "entry_price": rec_trade.get("entry_price"),
                        "position_size_pct": rec_trade.get("position_size_pct"),
                        "event": "SIGNAL"
                    }
                    feed.append({"type": "signal", "timestamp": ts, "data": signal_data})
            except Exception:
                pass

    # Sort by timestamp descending
    feed.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return feed[:15]


# ── API: Watchlist ─────────────────────────────────────────────────────────────
@app.get("/api/watchlist")
async def get_watchlist():
    try:
        with get_db() as db:
            row = db.execute("SELECT value_json FROM market_data WHERE key = 'watchlist'").fetchone()
            if row:
                return json.loads(row["value_json"])
    except Exception:
        pass
    return {"watchlist": ["BTC", "ETH", "SOL"], "updated_at": ""}


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
        with get_db() as db:
            row = db.execute("SELECT value_json FROM market_data WHERE key = 'market_intelligence'").fetchone()
            if row:
                intel_json = row["value_json"].replace("Nansen", "Smart Money Holder").replace("nansen", "smart money holder")
                intel.update(json.loads(intel_json))
            
            dec_row = db.execute("SELECT decision_json FROM decision_logs ORDER BY timestamp DESC LIMIT 1").fetchone()
            if dec_row and dec_row["decision_json"]:
                dj = json.loads(dec_row["decision_json"].replace("Nansen", "Smart Money Holder").replace("nansen", "smart money holder"))
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
def get_hl_top_perps():
    """Read top perps from the SQLite DB updated by the background service."""
    try:
        with get_db() as db:
            row = db.execute("SELECT value_json FROM market_data WHERE key = 'top_perps'").fetchone()
            if row:
                cached_data = json.loads(row["value_json"])
                return cached_data.get("data", {})
                
        # Fallback
        data = get_top_3_perps_with_details()
        return data
    except Exception as e:
        print(f"ERROR: /api/hl_top_perps: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── API: Equity Curve ─────────────────────────────────────────────────────────
@app.get("/api/equity_curve")
async def get_equity_curve():
    """Reconstruct equity curve from trade close events."""
    initial = 1000.0
    equity = initial
    now_ts = int(datetime.now(timezone.utc).timestamp())

    # Start point (24h ago or trade start)
    curve = [{"time": now_ts - 86400, "value": initial}]

    all_trades = sorted(_load_all_trades(), key=lambda x: x.get("timestamp", ""))

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
            # Avoid duplicate timestamps
            if curve and curve[-1]["time"] >= unix_ts:
                unix_ts = curve[-1]["time"] + 1
            curve.append({"time": unix_ts, "value": round(equity, 2)})

    # Current endpoint
    try:
        with open(LOGS_DIR / "portfolio_state.json") as f:
            state = json.load(f)
        equity = float(state.get("cash", equity))
    except Exception:
        pass

    if not curve or curve[-1]["time"] < now_ts:
        curve.append({"time": now_ts, "value": round(equity, 2)})

    return curve


# ── API: User Paper Trading ────────────────────────────────────────────────────
@app.post("/api/papertrade/register")
async def register_paper_trader(body: dict):
    """Register a new user for paper trading. Returns a user_id."""
    name = body.get("name", "Anonymous")
    data = _load_users()

    user_id = str(uuid.uuid4())[:8]
    data["paper_traders"][user_id] = {
        "name": name,
        "cash": 1000.0,
        "realized_pnl": 0.0,
        "total_trades": 0,
        "winning_trades": 0,
        "positions": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_users(data)
    return {"user_id": user_id, "message": f"Paper trading account created for {name}"}


@app.get("/api/papertrade/{user_id}")
async def get_paper_trader(user_id: str):
    data = _load_users()
    user = data["paper_traders"].get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    total = user["total_trades"]
    wins = user["winning_trades"]
    return {
        **user,
        "win_rate": round((wins / total * 100) if total > 0 else 0, 1),
        "equity": round(user["cash"] + user["realized_pnl"], 2),
    }


@app.get("/api/papertrade/{user_id}/leaderboard")
async def get_leaderboard():
    data = _load_users()
    board = [
        {
            "user_id": uid,
            "name": u["name"],
            "equity": round(u["cash"] + u["realized_pnl"], 2),
        }
        for uid, u in data["paper_traders"].items()
    ]
    return sorted(board, key=lambda x: x["equity"], reverse=True)[:10]

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

class TradeCoinReq(BaseModel):
    coin: str

_hl_client = None
def get_hl_client():
    global _hl_client
    if _hl_client is None:
        from backend.hyperliquid_client import HyperliquidManualClient
        _hl_client = HyperliquidManualClient()
    return _hl_client

@app.post("/api/trade/open")
def manual_trade_open(req: TradeOpenReq):
    try:
        client = get_hl_client()
        res = client.open_position(
            req.coin, req.side, req.size_usd, req.leverage,
            req.is_limit, req.limit_price, req.sl_price, req.tp_price
        )
        if res.get("status") == "error":
            raise HTTPException(status_code=400, detail=res.get("message"))
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trade/close")
def manual_trade_close(req: TradeCoinReq):
    try:
        client = get_hl_client()
        res = client.close_position(req.coin)
        if res.get("status") == "error":
            raise HTTPException(status_code=400, detail=res.get("message"))
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trade/reverse")
def manual_trade_reverse(req: TradeCoinReq):
    try:
        client = get_hl_client()
        res = client.reverse_position(req.coin)
        if res.get("status") == "error":
            raise HTTPException(status_code=400, detail=res.get("message"))
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wallet/balance")
def get_wallet_balance(wallet: Optional[str] = None):
    try:
        # Accept wallet from query param (frontend localStorage) or fall back to env
        addr = (wallet or os.environ.get("HL_WALLET", "")).strip()
        if not addr:
            return {"balance": 0, "available": 0, "configured": False, "reason": "No wallet configured"}
        # Also sync to env so subsequent trade calls work
        os.environ["HL_WALLET"] = addr
        from hyperliquid.info import Info
        from hyperliquid.utils import constants
        info = Info(base_url=constants.MAINNET_API_URL, skip_ws=True)
        state = info.user_state(addr)
        margin = state.get("marginSummary", {})
        account_value = float(margin.get("accountValue", 0))
        available = float(state.get("withdrawable", account_value))
        return {"balance": round(account_value, 2), "available": round(available, 2), "configured": True}
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
def get_all_coins():
    try:
        from hyperliquid.info import Info
        from hyperliquid.utils import constants
        info = Info(base_url=constants.MAINNET_API_URL, skip_ws=True)
        meta = info.meta()
        coins = [asset["name"].upper() for asset in meta.get("universe", [])]
        return {"coins": sorted(coins)}
    except Exception as e:
        return {"coins": ["BTC", "ETH", "SOL", "AVAX", "DOGE"], "error": str(e)}

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
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE LOWER(wallet_address) = ?", (wallet,)).fetchone()
        if not user:
            db.execute("INSERT INTO users (wallet_address) VALUES (?)", (req.wallet_address,))
    return {"status": "success"}

@app.get("/api/auth/me")
async def auth_me(wallet: str):
    w = wallet.lower()
    with get_db() as db:
        user = db.execute("SELECT wallet_address, email FROM users WHERE LOWER(wallet_address) = ?", (w,)).fetchone()
        if not user:
            # Return empty structure if not found, since frontend might check connection blindly
            return {"wallet_address": wallet, "email": "", "subscriptions": []}
            
        subs = db.execute("SELECT * FROM subscriptions WHERE LOWER(wallet_address) = ? AND status = 'ACTIVE'", (w,)).fetchall()
        
        return {
            "wallet_address": user["wallet_address"],
            "email": user["email"],
            "subscriptions": [dict(s) for s in subs]
        }



class KeysReq(BaseModel):
    hl_private_key: Optional[str] = None
    hl_wallet: Optional[str] = None
    email: Optional[str] = None

@app.post("/api/settings/keys")
async def save_hl_keys(req: KeysReq):
    import os
    import dotenv
    env_path = ROOT / ".env"

    try:
        if req.hl_private_key:
            # Validate private key is a valid Ethereum key
            from eth_account import Account as _Account
            _Account.from_key(req.hl_private_key)  # raises if invalid
            dotenv.set_key(str(env_path), "HL_PRIVATE_KEY", req.hl_private_key)
            os.environ["HL_PRIVATE_KEY"] = req.hl_private_key

        if req.hl_wallet:
            dotenv.set_key(str(env_path), "HL_WALLET", req.hl_wallet)
            os.environ["HL_WALLET"] = req.hl_wallet

        if req.hl_wallet and req.email:
            with get_db() as db:
                db.execute("UPDATE users SET email = ? WHERE LOWER(wallet_address) = ?", (req.email, req.hl_wallet.lower()))

        # Reset the manual client so next trade picks up fresh keys
        global _hl_client
        _hl_client = None

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
        with get_db() as db:
            rows = db.execute("SELECT * FROM strategies").fetchall()
            strats = []
            for r in rows:
                strat = dict(r)
                try:
                    strat["tags"] = json.loads(strat["tags"])
                except:
                    strat["tags"] = []
                
                # Fetch cached backtest metrics for this coin
                cache_row = db.execute("SELECT metrics_json FROM backtest_cache WHERE strategy_id = ? AND timeframe = ? AND coin = ?", (strat["id"], "1h", coin)).fetchone()
                if cache_row:
                    strat["metrics"] = json.loads(cache_row["metrics_json"])
                else:
                    # Default mock metrics until backtester runs
                    strat["metrics"] = {
                        "winRate": 65.5,
                        "totalPnl": 850.2,
                        "drawdown": 4.5,
                        "trades": 120
                    }
                strats.append(strat)
            return strats
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/strategies/subscribe")
async def subscribe_strategy(req: SubscribeRequest):
    with get_db() as db:
        # Check limit
        count = db.execute("SELECT count(*) as c FROM subscriptions WHERE wallet_address = ?", (req.wallet_address,)).fetchone()["c"]
        if count >= 5:
            raise HTTPException(status_code=400, detail="Maximum 5 strategies allowed per user.")
        
        # Check strategy state
        state = db.execute("SELECT status FROM strategy_state WHERE strategy_id = ?", (req.strategy_id,)).fetchone()
        strat_status = state["status"] if state else "FLAT"
        
        sub_status = "WAITING" if strat_status == "IN_TRADE" else "ACTIVE"
        
        try:
            db.execute('''
                INSERT INTO subscriptions (wallet_address, strategy_id, coin, status, capital, leverage, timeframe)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (req.wallet_address, req.strategy_id, req.coin, sub_status, req.capital, req.leverage, req.timeframe))
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Already subscribed to this strategy.")
            
        return {"status": "success", "subscription_status": sub_status}

@app.post("/api/strategies/{strategy_id}/backtest")
async def run_backtest(strategy_id: str, timeframe: str = "1h", coin: str = "BTC"):
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
        
        # Calculate candles for 30 days (1 month)
        tf_candles = {'1m': 43200, '5m': 8640, '15m': 2880, '1h': 720, '4h': 180, '1d': 30}
        # Cap at 2000 for safety to not overload the API or frontend
        target_n = min(2000, max(50, tf_candles.get(timeframe, 720)))
        
        df = fetch_candles(coin, interval=timeframe, n=target_n)
        
        if not df.empty:
            # Run the real backtest simulation
            results = run_simulation(df, strategy_id=strategy_id, initial_capital=1000.0, leverage=1)
            metrics = results["metrics"]
            trades = results["trades"]
            
    except Exception as e:
        import traceback
        print(f"Error running backtest: {e}")
        traceback.print_exc()

    with get_db() as db:
        metrics_json = json.dumps(metrics)
        db.execute('''
            INSERT INTO backtest_cache (strategy_id, timeframe, coin, metrics_json, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(strategy_id, timeframe, coin) DO UPDATE SET 
            metrics_json = excluded.metrics_json,
            updated_at = CURRENT_TIMESTAMP
        ''', (strategy_id, timeframe, coin, metrics_json))
        
    return {"status": "success", "metrics": metrics, "trades": trades}

# ── API: AI Chat ─────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    prompt: str
    context_type: str = "general"

def _build_context(db, context_type: str) -> str:
    """Build a concise, deduplicated context string for Claude."""
    parts = []

    if context_type in ("market_analysis", "general"):
        row = db.execute("SELECT value_json FROM market_data WHERE key = 'market_intelligence'").fetchone()
        if row:
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
        strats = db.execute("SELECT name, tags FROM strategies").fetchall()
        if strats:
            strat_lines = [f"{s['name']} ({s['tags']})" for s in strats]
            parts.append(f"AVAILABLE STRATEGIES ({len(strats)} total):\n" + "\n".join(strat_lines))

    if context_type in ("smart_money_holder", "general"):
        rows = db.execute("SELECT endpoint, response_json FROM nansen_cache ORDER BY timestamp DESC LIMIT 3").fetchall()
        if rows:
            sm_parts = ["SMART MONEY HOLDER DATA:"]
            for r in rows:
                sm_parts.append(f"[{r['endpoint']}]\n{r['response_json'][:1500]}")
            parts.append("\n".join(sm_parts))

    if context_type in ("risk_management", "general"):
        trades = db.execute(
            "SELECT coin, side, entry_price, exit_price, pnl_usd, action, timestamp FROM trade_logs ORDER BY timestamp DESC LIMIT 8"
        ).fetchall()
        if trades:
            trade_lines = [f"- {dict(t)}" for t in trades]
            parts.append("USER RECENT TRADES:\n" + "\n".join(trade_lines))

    # Scrub 'nansen' from the context before giving it to Claude
    final_context = "\n\n".join(parts)
    final_context = final_context.replace("Nansen", "Smart Money").replace("nansen", "smart money")
    
    return final_context

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "sk-ant-your-key-here":
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")

    import hashlib
    from datetime import datetime, timezone, timedelta

    # TTL per context type (seconds). risk_management is shorter as it's user-specific.
    TTL_MAP = {
        "strategy_generation": 7200,   # 2 hours — strategies rarely change
        "market_analysis":     1800,   # 30 minutes
        "smart_money_holder":  1800,   # 30 minutes
        "risk_management":     900,    # 15 minutes — user trades change frequently
        "general":             900,    # 15 minutes
    }
    ttl_seconds = TTL_MAP.get(req.context_type, 900)

    # Build deterministic cache key from normalized prompt + context_type
    normalized = f"{req.prompt.strip().lower()}|{req.context_type}"
    cache_key = hashlib.sha256(normalized.encode()).hexdigest()

    SIMILARITY_THRESHOLD = 0.88  # 88% cosine similarity = semantic match

    # ── Tier 1: Exact hash match (free, instant) ──────────────────────────────
    cached_response = None
    matched_key = None
    with get_db() as db:
        row = db.execute(
            "SELECT response FROM chat_cache WHERE cache_key = ? AND expires_at > CURRENT_TIMESTAMP",
            (cache_key,)
        ).fetchone()
        if row:
            cached_response = row["response"]
            matched_key = cache_key

    # ── Tier 2: Semantic similarity search (handles synonyms) ─────────────────
    if cached_response is None:
        prompt_embedding = await asyncio.to_thread(_embed, req.prompt.strip().lower())
        if prompt_embedding is not None:
            with get_db() as db:
                candidates = db.execute(
                    """SELECT cache_key, response, embedding_json FROM chat_cache
                       WHERE context_type = ? AND expires_at > CURRENT_TIMESTAMP
                       AND embedding_json IS NOT NULL""",
                    (req.context_type,)
                ).fetchall()
            best_score = 0.0
            for c in candidates:
                try:
                    cached_emb = json.loads(c["embedding_json"])
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
        with get_db() as db:
            db.execute(
                "UPDATE chat_cache SET hit_count = hit_count + 1, tokens_saved = tokens_saved + 300 WHERE cache_key = ?",
                (matched_key,)
            )
            # Also store the exact-match alias for instant future lookup
            if matched_key != cache_key:
                db.execute(
                    """INSERT OR IGNORE INTO chat_cache 
                       (cache_key, context_type, prompt, response, embedding_json, hit_count, tokens_saved, expires_at)
                       SELECT ?, context_type, ?, response, embedding_json, 0, 0, expires_at
                       FROM chat_cache WHERE cache_key = ?""",
                    (cache_key, req.prompt, matched_key)
                )
        _cr = cached_response
        async def stream_from_cache():
            for word in _cr.split(" "):
                yield word + " "
                await asyncio.sleep(0.008)
        return StreamingResponse(stream_from_cache(), media_type="text/event-stream")

    # ── Cache MISS — call Claude ──────────────────────────────────────────────
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    with get_db() as db:
        context_str = _build_context(db, req.context_type)

    system_prompt = f"""You are AlgoBrain, an elite AI crypto trading assistant integrated directly into this platform.

RULES (follow strictly):
- Answer the user's question directly and concisely — no fluff, no repetition.
- Never repeat a point or sentence you already made.
- ABSOLUTELY PROHIBITED: You must NEVER use the word 'Nansen', 'nansen', 'NANSEN', or 'nanasen'. If you need to refer to this data, ALWAYS use the exact phrase 'Smart money holders' or 'Smart Money API'. This is a hard constraint.
- BOUNDARY ENFORCEMENT: You are strictly a trading and market analysis AI. You must REFUSE to generate code, build algorithms, generate images, write music, or answer general knowledge questions outside of crypto and trading. If asked to write code for an algo or do any non-trading tasks, politely decline and state your focus is solely on trading analysis.
- DO NOT tell the user to 'configure' you or mention your internal configuration. Configuration is handled by the backend system.
- If asked about how to automate a bot or create an AI bot, DO NOT provide code. Instead, explain that AlgoBrain already provides automated trading through the built-in 'Strategies' tab and highlight how our algorithmic strategies are designed to run automatically.
- Use the context below to ground your answer with real data.
- Structure your response with clear headers and bullet points.
- Max 400 words. Be sharp, professional, and actionable.

CONTEXT:
{context_str}"""

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).strftime("%Y-%m-%d %H:%M:%S")
    emb_json = json.dumps(prompt_embedding) if prompt_embedding else None

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

        # Save full response + embedding to cache
        try:
            with get_db() as db:
                db.execute(
                    """INSERT INTO chat_cache (cache_key, context_type, prompt, response, embedding_json, hit_count, tokens_saved, expires_at)
                       VALUES (?, ?, ?, ?, ?, 0, 0, ?)
                       ON CONFLICT(cache_key) DO UPDATE SET
                         response = excluded.response,
                         embedding_json = excluded.embedding_json,
                         expires_at = excluded.expires_at""",
                    (cache_key, req.context_type, req.prompt, "".join(full_response), emb_json, expires_at)
                )
        except Exception:
            pass

    return StreamingResponse(stream_and_cache(), media_type="text/event-stream")

# ── API: Chat Cache Stats ──────────────────────────────────────────────────────
@app.get("/api/chat/cache-stats")
async def chat_cache_stats():
    """Returns cache hit statistics and estimated token savings."""
    with get_db() as db:
        rows = db.execute(
            """SELECT context_type, COUNT(*) as entries,
               SUM(hit_count) as total_hits,
               SUM(tokens_saved) as total_tokens_saved
               FROM chat_cache
               WHERE expires_at > CURRENT_TIMESTAMP
               GROUP BY context_type"""
        ).fetchall()
        total = db.execute(
            "SELECT COUNT(*) as c, SUM(hit_count) as h, SUM(tokens_saved) as t FROM chat_cache"
        ).fetchone()
    return {
        "by_context": [dict(r) for r in rows],
        "total_cached_prompts": total["c"] or 0,
        "total_cache_hits": total["h"] or 0,
        "total_tokens_saved": total["t"] or 0,
    }

class FeedbackRequest(BaseModel):
    message_index: int
    feedback: str
    text: str

@app.post("/api/ai/feedback")
async def ai_feedback(req: FeedbackRequest):
    """Stores user thumbs up/down feedback on AI responses, toggling if already set."""
    try:
        with get_db() as db:
            # First, clear any existing feedback for this message index in this session
            db.execute("DELETE FROM ai_feedback WHERE message_index = ?", (req.message_index,))
            
            # If the feedback is not 'none', insert the new state
            if req.feedback != 'none':
                db.execute(
                    "INSERT INTO ai_feedback (message_index, feedback, text) VALUES (?, ?, ?)",
                    (req.message_index, req.feedback, req.text)
                )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Make sure DB is initialized
    from backend.db import init_db
    init_db()
    
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}...")
    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, reload=True)
