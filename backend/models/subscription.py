from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class Strategy(BaseModel):
    id: str
    name: str
    description: str
    tags: str # JSON string of list

class StrategyState(BaseModel):
    strategy_id: str
    status: str = "FLAT" # 'FLAT' or 'IN_TRADE'
    active_coin: Optional[str] = None
    active_direction: Optional[str] = None

class Subscription(BaseModel):
    wallet_address: str
    strategy_id: str
    status: str = "WAITING" # 'WAITING' or 'ACTIVE'
    capital: float
    leverage: int
    timeframe: str
    target_pct: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    asset_name: Optional[str] = None
    ai_engine: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
