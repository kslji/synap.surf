from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class User(BaseModel):
    wallet_address: str
    private_key: Optional[str] = None
    email: Optional[str] = None
    telegram_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
