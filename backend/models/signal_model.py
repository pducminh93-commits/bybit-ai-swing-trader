from pydantic import BaseModel
from typing import Optional, Dict, Any

class SignalResponse(BaseModel):
    symbol: str
    signal: str  # BUY, SELL, HOLD
    confidence: float
    reason: str
    take_profit: float
    stop_loss: float
    indicators: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None