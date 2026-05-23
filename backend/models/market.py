from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class MarketData(BaseModel):
    key: str
    value_json: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class NansenCache(BaseModel):
    endpoint: str
    cache_key: str
    response_json: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class BacktestCache(BaseModel):
    strategy_id: str
    timeframe: str
    metrics_json: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)
