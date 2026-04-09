from pydantic import BaseModel
from typing import Optional, Dict, Any

class SignalResponse(BaseModel):
    symbol: str
    signal: str  # LONG, SHORT, HOLD, EXIT
    confidence: float
    reason: str
    take_profit: float
    stop_loss: float
    entry_price: Optional[float] = None
    indicators: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None