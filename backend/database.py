import os
from typing import Optional
from dotenv import load_dotenv
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

MONGO_URL = os.getenv('MONGO_URL')

if not MONGO_URL:
    raise ValueError("MONGO_URL is not set in the .env file")

# ── Synchronous Client (for PM2 worker scripts: maintainer, executor) ──
_sync_client: Optional[MongoClient] = None

def get_sync_db():
    global _sync_client
    if _sync_client is None:
        _sync_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    return _sync_client.algo_brain

# ── Asynchronous Client (for FastAPI server) ──
_async_client: Optional[AsyncIOMotorClient] = None

def get_async_db():
    global _async_client
    if _async_client is None:
        _async_client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    return _async_client.algo_brain
