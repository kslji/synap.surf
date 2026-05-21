"""
dashboard/server.py — FastAPI backend for the AlgoBrain dashboard.

Reads from algo_brain/logs/ and serves:
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
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from algo_brain.market_data import get_top_3_perps_with_details, get_mid_prices
from algo_brain.config import HL_WALLET

import asyncio
from contextlib import asynccontextmanager
from backend.services import volatility_service, market_intel_service, trade_history_sync_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    task1 = asyncio.create_task(volatility_service())
    task2 = asyncio.create_task(market_intel_service())
    task3 = asyncio.create_task(trade_history_sync_service())
    yield
    # Shutdown
    task1.cancel()
    task2.cancel()
    task3.cancel()

app = FastAPI(title="AlgoBrain Dashboard", lifespan=lifespan)

ROOT = Path("/Users/arjunsingh/Desktop/algo_brain")
REACT_DIST = ROOT / "frontend" / "react-app" / "dist"
STATIC_DIR = ROOT / "frontend" / "static"
LOGS_DIR = ROOT / "algo_brain" / "logs"
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
                kv_row = db.execute("SELECT value_json FROM market_data WHERE key = 'live_positions'").fetchone()
            else:
                row = db.execute("SELECT * FROM portfolios WHERE user_id = 'PAPER_USER' AND portfolio_type = 'PAPER'").fetchone()
                kv_row = db.execute("SELECT value_json FROM market_data WHERE key = 'paper_positions'").fetchone()

            if not row and HL_WALLET:
                from algo_brain.telegram_bot import get_live_hl_portfolio
                live_data = get_live_hl_portfolio()
                if live_data:
                    return {
                        "equity": round(live_data["total_equity"], 2),
                        "cash": round(live_data["cash"], 2),
                        "realized_pnl": 0.0,
                        "unrealized_pnl": round(live_data["unrealized_pnl"], 2),
                        "total_trades": 0,
                        "winning_trades": 0,
                        "losing_trades": 0,
                        "win_rate": 0.0,
                        "fees_paid": round(live_data["cumulative_fees"], 2),
                        "pnl_pct": 0.0,
                        "positions": live_data["positions"],
                        "last_updated": live_data["fetched_at"],
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
            
            if HL_WALLET:
                # Live total_equity from DB already includes unrealized from the API fetch.
                equity = float(row["total_equity"])
            else:
                # Paper trades dynamically sum cash + unrealized
                equity = float(row["cash"]) + unrealized
            
            total_trades = row["total_trades"]
            winning_trades = row["winning_trades"]
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            pnl_pct = round((equity - initial_capital) / initial_capital * 100, 2)
            if HL_WALLET:
                # In live mode, we might not know initial capital. Using realized_pnl over cash as rough proxy or leave it 0 if we don't have accurate history.
                pnl_pct = 0.0 # Optionally leave out pct for live
            
            eth_price = get_mid_prices().get("ETH", 3200.0)
            
            return {
                "equity": round(equity, 2),
                "cash": round(float(row["cash"]), 2),
                "realized_pnl": round(float(row["realized_pnl"]), 2),
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
        from algo_brain.hyperliquid_trader import HyperliquidTrader
        # Instantiating the trader automatically fetches state or we can call fetch directly.
        # But trader._save_state() needs an active Info call. Actually get_live_hl_portfolio() is better.
        from algo_brain.telegram_bot import get_live_hl_portfolio
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
    # Load raw trade events from trades_*.jsonl
    trades = _load_all_trades()
    feed = []
    for t in trades:
        feed.append({"type": "trade_event", "timestamp": t.get("timestamp"), "data": t})

    # Sort by timestamp descending
    feed.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return feed[:10]


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
    try:
        with get_db() as db:
            row = db.execute("SELECT value_json FROM market_data WHERE key = 'market_intelligence'").fetchone()
            if row:
                return json.loads(row["value_json"])
    except Exception:
        pass
    return {
        "market_view": "Syncing market data...",
        "fear_greed": {"value": 50, "classification": "Neutral"},
        "trending_coins": [],
        "trending_narratives": []
    }


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
        from algo_brain.market_data import fetch_candles
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



class KeysReq(BaseModel):
    hl_private_key: Optional[str] = None
    hl_wallet: Optional[str] = None

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
        from algo_brain.market_data import fetch_candles
        from algo_brain.strategies.backtest import run_simulation
        
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

if __name__ == "__main__":
    import uvicorn
    # Make sure DB is initialized
    from backend.db import init_db
    init_db()
    
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}...")
    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, reload=True)
