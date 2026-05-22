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
    return {"subscribers": [], "paper_traders": {}}


def _save_users(data: dict) -> None:
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Helper: Load all JSONL trades ─────────────────────────────────────────────
def _load_all_trades(wallet: str = None) -> list[dict]:
    try:
        if not wallet or wallet in ('null', 'undefined', ''):
            return []
            
        with get_db() as db:
            rows = db.execute("SELECT * FROM trade_logs WHERE user_id = ? ORDER BY timestamp ASC", (wallet,)).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []

def _load_all_decisions(wallet: str = None) -> list[dict]:
    try:
        if not wallet or wallet in ('null', 'undefined', ''):
            return []
            
        with get_db() as db:
            rows = db.execute("SELECT * FROM decision_logs WHERE user_id = ? ORDER BY timestamp DESC", (wallet,)).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


# ── API: Portfolio Stats ───────────────────────────────────────────────────────
@app.get("/api/stats")
def get_stats(wallet: str = None):
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

        # Fetch real-time equity from Hyperliquid
        try:
            from hyperliquid.info import Info
            from hyperliquid.utils import constants
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            state = info.user_state(wallet)
            margin_summary = state.get("marginSummary", {})
            equity = float(margin_summary.get("accountValue", 0.0))
            
            positions = []
            for entry in state.get("assetPositions", []):
                pos = entry.get("position", {})
                if pos and float(pos.get("szi", 0)) != 0:
                    szi = float(pos["szi"])
                    entry_px = float(pos["entryPx"])
                    positions.append({
                        "coin": pos["coin"],
                        "side": "LONG" if szi > 0 else "SHORT",
                        "size": abs(szi),
                        "entry_price": entry_px,
                        "unrealized_pnl": float(pos["unrealizedPnl"])
                    })
        except Exception as e:
            print(f"Error fetching Hyperliquid state for {wallet}: {e}")
            equity = 0.0
            positions = []

        with get_db() as db:
            # Query their trades for stats
            trades = db.execute("SELECT * FROM trade_logs WHERE LOWER(user_id) = ?", (wallet.lower(),)).fetchall()
            trades_list = [dict(t) for t in trades]
            
            total_trades = len(trades_list)
            winning = sum(1 for t in trades_list if t.get("pnl_usd") and t.get("pnl_usd") > 0)
            losing = sum(1 for t in trades_list if t.get("pnl_usd") is not None and t.get("pnl_usd") <= 0 and t.get("event") == "TRADE_CLOSE")
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
                "last_updated": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── API: Recent Trades ─────────────────────────────────────────────────────────
@app.get("/api/trades")
async def get_trades(wallet: str = None):
    trades = _load_all_trades(wallet)
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
async def refresh_portfolio(req: Request):
    data = await req.json()
    wallet = data.get("wallet_address")
    if not wallet:
        raise HTTPException(status_code=400, detail="wallet_address required")
    # For now, this is a no-op since positions will be updated by execution_engine
    return {"status": "ok", "message": "Refresh requested"}

@app.post("/api/strategy/subscribe")
async def subscribe_strategy(request: Request):
    """User selects a strategy. If IN_TRADE, they join the waiting room."""
    data = await request.json()
    wallet_address = data.get("wallet_address")
    strategy_id = data.get("strategy_id")
    capital = data.get("capital", 100)
    leverage = data.get("leverage", 10)
    timeframe = data.get("timeframe", "1h")
    
    target_pct = data.get("target_pct") # None means AUTO
    stop_loss_pct = data.get("stop_loss_pct") # None means AUTO
    asset_name = data.get("asset_name", "AUTO")
    ai_engine = data.get("ai_engine", "CLAUDE")
    
    if not strategy_id or not wallet_address:
        raise HTTPException(status_code=400, detail="strategy_id and wallet_address required")
        
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
                INSERT INTO subscriptions (wallet_address, strategy_id, status, capital, leverage, timeframe, target_pct, stop_loss_pct, asset_name, ai_engine)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(wallet_address, strategy_id) DO UPDATE SET
                    status=excluded.status,
                    capital=excluded.capital,
                    leverage=excluded.leverage,
                    timeframe=excluded.timeframe,
                    target_pct=excluded.target_pct,
                    stop_loss_pct=excluded.stop_loss_pct,
                    asset_name=excluded.asset_name,
                    ai_engine=excluded.ai_engine
            ''', (wallet_address, strategy_id, status, capital, leverage, timeframe, target_pct, stop_loss_pct, asset_name, ai_engine))
            
        return {"status": "ok", "subscription_status": status, "alert": alert_msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── API: AI Signals (Clean Feed) ──────────────────────────────────────────────
@app.get("/api/decisions")
async def get_decisions(wallet: str = None):
    trades = _load_all_trades(wallet)
    decisions_raw = _load_all_decisions(wallet)
    
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
            
            # Instead of picking a random user's decision_log, use the global AI master decision
            global_row = db.execute("SELECT value_json FROM market_data WHERE key = 'market_intelligence_global'").fetchone()
            if global_row and global_row["value_json"]:
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
async def get_equity_curve(wallet: str = None):
    """Reconstruct equity curve from trade close events."""
    if not wallet or wallet in ('null', 'undefined', ''):
        return []
        
    initial = 1000.0
    equity = initial
    now_ts = int(datetime.now(timezone.utc).timestamp())

    curve = [{"time": now_ts - 86400, "value": initial}]

    all_trades = sorted(_load_all_trades(wallet), key=lambda x: x.get("timestamp", ""))

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
        with get_db() as db:
            row = db.execute("SELECT cash, total_equity FROM portfolios WHERE user_id = ?", (wallet,)).fetchone()
            if row:
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

class TradeCoinReq(BaseModel):
    coin: str
    wallet_address: str

def get_hl_client(wallet_address: str):
    from backend.db import get_db
    with get_db() as db:
        user = db.execute("SELECT private_key FROM users WHERE LOWER(wallet_address) = ?", (wallet_address.lower(),)).fetchone()
        if not user or not user["private_key"]:
            raise ValueError("No private key configured for this wallet")
        
        from synap.hyperliquid_trader import HyperliquidTrader
        return HyperliquidTrader(private_key=user["private_key"], wallet_address=wallet_address)

@app.post("/api/trade/open")
def manual_trade_open(req: TradeOpenReq):
    try:
        client = get_hl_client(req.wallet_address)
        
        # HyperliquidTrader uses slightly different args than HyperliquidManualClient
        res = client.open_position(
            coin=req.coin, 
            side=req.side, 
            entry_price=req.limit_price or 0.0,
            size_usd=req.size_usd, 
            leverage=req.leverage,
            stop_loss=req.sl_price or 0.0,
            tp1=req.tp_price or 0.0
        )
        if not res:
            raise HTTPException(status_code=400, detail=res.get("message"))
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trade/close")
def manual_trade_close(req: TradeCoinReq):
    try:
        client = get_hl_client(req.wallet_address)
        res = client.close_position(req.coin, 0.0)
        if not res:
            raise HTTPException(status_code=400, detail=res.get("message"))
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trade/reverse")
def manual_trade_reverse(req: TradeCoinReq):
    try:
        client = get_hl_client(req.wallet_address)
        # Assuming HyperliquidTrader has reverse_position, or we can just close and open opposite
        res = client.close_position(req.coin, 0.0)
        if not res:
            raise HTTPException(status_code=400, detail=res.get("message"))
        return res
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
    try:
        wallet_addr = req.hl_wallet
        if not wallet_addr:
            raise ValueError("wallet address is required")

        updates = []
        params = []
        
        if req.hl_private_key:
            # Validate private key is a valid Ethereum key
            from eth_account import Account as _Account
            account = _Account.from_key(req.hl_private_key)  # raises if invalid
            updates.append("private_key = ?")
            params.append(req.hl_private_key)
            
        if req.email:
            updates.append("email = ?")
            params.append(req.email)
            
        if updates:
            params.append(wallet_addr.lower())
            query = f"UPDATE users SET {', '.join(updates)} WHERE LOWER(wallet_address) = ?"
            with get_db() as db:
                db.execute(query, params)

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

# Duplicate endpoint removed

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
    wallet: Optional[str] = None

def _build_context(db, context_type: str, wallet: str = None) -> str:
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
        if wallet:
            trades = db.execute(
                "SELECT coin, side, entry_price, exit_price, pnl_usd, action, timestamp FROM trade_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 8",
                (wallet,)
            ).fetchall()
        else:
            trades = []
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

    # Build deterministic cache key from normalized prompt + context_type + wallet
    normalized = f"{req.prompt.strip().lower()}|{req.context_type}|{req.wallet or ''}"
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
        context_str = _build_context(db, req.context_type, req.wallet)

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
