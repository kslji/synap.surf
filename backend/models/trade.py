from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class TradeLog(BaseModel):
    strategy_id: str
    asset: str
    side: str
    size: float
    price: float
    reason: str
    event: str # e.g. 'ENTRY', 'EXIT', 'FILL'
    pnl: Optional[float] = None
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class DecisionLog(BaseModel):
    strategy_id: str
    decision_json: str
    raw_prompt_size: int = 0
    raw_response_size: int = 0
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
