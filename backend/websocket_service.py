import asyncio
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import websockets
from bson import ObjectId
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend directory is in path for db import
sys.path.append(str(Path(__file__).parent.parent))
from backend.database import get_async_db
from backend.trade_sync import _fill_to_doc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("websocket_service")

app = FastAPI(title="AlgoBrain WebSocket Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _serialize_trade_doc(doc: dict) -> dict:
    out: dict = {}
    for key, val in doc.items():
        if isinstance(val, ObjectId):
            out[key] = str(val)
        elif isinstance(val, datetime):
            out[key] = val.isoformat()
        else:
            out[key] = val
    return out

class TradeConnMgr:
    def __init__(self):
        self._conns: Dict[str, List[WebSocket]] = {}

    async def connect(self, wallet: str, ws: WebSocket):
        await ws.accept()
        self._conns.setdefault(wallet.lower(), []).append(ws)
        logger.info(f"Client connected for wallet: {wallet}")

    def disconnect(self, wallet: str, ws: WebSocket):
        conns = self._conns.get(wallet.lower(), [])
        if ws in conns:
            conns.remove(ws)
        logger.info(f"Client disconnected for wallet: {wallet}")

    async def push(self, wallet: str, payload: dict):
        if isinstance(payload.get("trades"), list):
            payload = {
                **payload,
                "trades": [_serialize_trade_doc(t) for t in payload["trades"] if isinstance(t, dict)],
            }
        dead = []
        for ws in self._conns.get(wallet.lower(), []):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._conns[wallet.lower()].remove(ws)

trade_mgr = TradeConnMgr()

# Hyperliquid Websocket Ingestion
async def _handle_hl_ws_message(msg_str: str, db):
    try:
        msg = json.loads(msg_str)
        if msg.get("channel") == "userEvents":
            data = msg.get("data", {})
            fills = data.get("fills", [])
            for fill in fills:
                wallet = fill.get("user")
                if not wallet:
                    continue
                
                tid = fill.get("tid")
                # Check if it exists
                existing = None
                if tid is not None:
                    existing = await db.trade_logs.find_one({
                        "user_id": re.compile(f"^{re.escape(wallet)}$", re.IGNORECASE),
                        "hl_tid": tid,
                    })
                
                if not existing:
                    doc = _fill_to_doc(wallet, fill)
                    await db.trade_logs.insert_one(doc)
                    logger.info(f"Ingested new fill via WS for {wallet}: {fill.get('coin')} {doc['side']}")
                    
                    # Push to connected clients immediately
                    doc["_id"] = str(doc.get("_id", ""))
                    await trade_mgr.push(wallet, {"type": "new_trades", "trades": [doc]})
    except Exception as e:
        logger.error(f"Error handling HL WS message: {e}")

async def hyperliquid_ws_ingestion_task():
    logger.info("Starting Hyperliquid WebSocket Ingestion Task...")
    uri = "wss://api.hyperliquid.xyz/ws"
    
    while True:
        try:
            db = get_async_db()
            # Get all registered wallets
            rows = await db.users.find({}).to_list(length=None)
            wallets = [r.get("wallet_address") for r in rows if r.get("wallet_address")]
            
            if not wallets:
                await asyncio.sleep(10)
                continue

            async with websockets.connect(uri) as websocket:
                logger.info(f"Connected to Hyperliquid WS. Subscribing to {len(wallets)} wallets.")
                
                for wallet in wallets:
                    sub_msg = {
                        "method": "subscribe",
                        "subscription": {"type": "userEvents", "user": wallet}
                    }
                    await websocket.send(json.dumps(sub_msg))
                
                while True:
                    msg = await websocket.recv()
                    await _handle_hl_ws_message(msg, db)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Hyperliquid WS connection closed. Reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Hyperliquid WS Error: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(hyperliquid_ws_ingestion_task())

@app.websocket("/ws/trades/{wallet}")
async def ws_trades(websocket: WebSocket, wallet: str):
    await trade_mgr.connect(wallet, websocket)
    try:
        db = get_async_db()
        q = {"$or": [
            {"user_id": re.compile(f"^{wallet}$", re.IGNORECASE)},
            {"wallet_address": re.compile(f"^{wallet}$", re.IGNORECASE)},
        ]}
        recent_raw = await db.trade_logs.find(q).sort("timestamp", -1).limit(20).to_list(20)
        recent = [_serialize_trade_doc(t) for t in recent_raw]
        await websocket.send_json({"type": "history", "trades": recent})
        last_ts = recent_raw[0]["timestamp"] if recent_raw else ""

        # Poll every 2s for new trades (in case they come from REST sync or manual closes)
        while True:
            await asyncio.sleep(2)
            extra = {"timestamp": {"$gt": last_ts}} if last_ts else {}
            new_raw = await db.trade_logs.find({**q, **extra}).sort("timestamp", -1).limit(10).to_list(10)
            if new_raw:
                new = [_serialize_trade_doc(t) for t in new_raw]
                last_ts = new_raw[0]["timestamp"]
                await websocket.send_json({"type": "new_trades", "trades": new})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS /ws/trades/{wallet}: {e}")
    finally:
        trade_mgr.disconnect(wallet, websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("websocket_service:app", host="0.0.0.0", port=8001, reload=True)
