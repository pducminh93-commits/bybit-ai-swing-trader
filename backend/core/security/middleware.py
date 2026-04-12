from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from typing import Optional, Dict, Any
import time
import hashlib
from collections import defaultdict

# Rate limiting storage (in production, use Redis)
rate_limit_store: Dict[str, Dict[str, Any]] = defaultdict(dict)


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed based on rate limit"""
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window

        if client_id not in rate_limit_store:
            rate_limit_store[client_id] = {
                "requests": [],
                "blocked_until": 0
            }

        client_data = rate_limit_store[client_id]

        # Check if client is currently blocked
        if current_time < client_data["blocked_until"]:
            return False

        # Clean old requests outside the window
        client_data["requests"] = [
            req_time for req_time in client_data["requests"]
            if req_time > window_start
        ]

        # Check rate limit
        if len(client_data["requests"]) >= self.requests_per_minute:
            # Block for 1 minute
            client_data["blocked_until"] = current_time + 60
            return False

        # Add current request
        client_data["requests"].append(current_time)
        return True

    def get_client_id(self, request: Request) -> str:
        """Generate client ID from request"""
        # Use IP address and user agent for identification
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Create hash for consistent ID
        id_string = f"{client_ip}:{user_agent}"
        return hashlib.md5(id_string.encode()).hexdigest()


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limiting_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Skip rate limiting for certain endpoints
    if request.url.path in ["/", "/docs", "/openapi.json"]:
        return await call_next(request)

    client_id = rate_limiter.get_client_id(request)

    if not rate_limiter.is_allowed(client_id):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "type": "RateLimitExceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 60
                }
            },
            headers={"Retry-After": "60"}
        )

    response = await call_next(request)
    return response


# Input validation models
class BacktestRequest(BaseModel):
    """Validation model for backtest requests"""
    symbol: str
    days: Optional[int] = 30
    leverage: Optional[float] = 10.0
    min_hold_candles: Optional[int] = 6
    stop_loss_pct: Optional[float] = 0.05

    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Symbol cannot be empty')
        if not v.isalnum() or len(v) > 20:
            raise ValueError('Invalid symbol format')
        return v.upper()

    @validator('days')
    def validate_days(cls, v):
        if v is not None and (v < 1 or v > 365):
            raise ValueError('Days must be between 1 and 365')
        return v

    @validator('leverage')
    def validate_leverage(cls, v):
        if v is not None and (v < 1 or v > 100):
            raise ValueError('Leverage must be between 1 and 100')
        return v

    @validator('min_hold_candles')
    def validate_min_hold_candles(cls, v):
        if v is not None and (v < 1 or v > 100):
            raise ValueError('Min hold candles must be between 1 and 100')
        return v

    @validator('stop_loss_pct')
    def validate_stop_loss_pct(cls, v):
        if v is not None and (v <= 0 or v > 1):
            raise ValueError('Stop loss percentage must be between 0 and 1')
        return v


class SignalRequest(BaseModel):
    """Validation model for signal requests"""
    symbol: str
    use_multiframe: Optional[bool] = True

    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Symbol cannot be empty')
        if not v.isalnum() or len(v) > 20:
            raise ValueError('Invalid symbol format')
        return v.upper()


class TrainUniversalRequest(BaseModel):
    """Validation model for universal model training"""
    symbols: str

    @validator('symbols')
    def validate_symbols(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Symbols list cannot be empty')

        symbol_list = [s.strip() for s in v.split(',') if s.strip()]
        if len(symbol_list) == 0:
            raise ValueError('At least one symbol must be provided')

        if len(symbol_list) > 10:
            raise ValueError('Maximum 10 symbols allowed for training')

        # Validate each symbol
        for symbol in symbol_list:
            if not symbol.isalnum() or len(symbol) > 20:
                raise ValueError(f'Invalid symbol format: {symbol}')

        return ','.join(symbol.upper() for symbol in symbol_list)


class TrainMLRequest(BaseModel):
    """Validation model for ML model training"""
    symbol: str
    model_type: Optional[str] = "rf"

    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Symbol cannot be empty')
        if not v.isalnum() or len(v) > 20:
            raise ValueError('Invalid symbol format')
        return v.upper()

    @validator('model_type')
    def validate_model_type(cls, v):
        allowed_types = ['rf', 'gb', 'ensemble']
        if v not in allowed_types:
            raise ValueError(f'Model type must be one of: {allowed_types}')
        return v


class DemoSettingsRequest(BaseModel):
    """Validation model for demo settings"""
    capital: Optional[float] = None
    leverage: Optional[float] = None
    position_size_pct: Optional[float] = None
    reset_data: Optional[bool] = False

    @validator('capital')
    def validate_capital(cls, v):
        if v is not None and (v < 10 or v > 1000000):
            raise ValueError('Capital must be between 10 and 1,000,000')
        return v

    @validator('leverage')
    def validate_leverage(cls, v):
        if v is not None and (v < 1 or v > 100):
            raise ValueError('Leverage must be between 1 and 100')
        return v

    @validator('position_size_pct')
    def validate_position_size_pct(cls, v):
        if v is not None and (v <= 0 or v > 100):
            raise ValueError('Position size percentage must be between 0 and 100')
        return v


def validate_input_data(data: Dict[str, Any], model_class) -> Dict[str, Any]:
    """Validate input data using Pydantic model"""
    try:
        validated_model = model_class(**data)
        return validated_model.dict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input validation failed: {str(e)}"
        )


async def input_validation_middleware(request: Request, call_next):
    """Input validation middleware"""
    # Only validate POST/PUT requests with JSON bodies
    if request.method in ['POST', 'PUT'] and 'application/json' in request.headers.get('content-type', ''):
        try:
            # Read and parse JSON body
            body = await request.json()

            # Validate based on endpoint
            if request.url.path == '/api/backtest':
                validate_input_data(body, BacktestRequest)
            elif request.url.path.startswith('/api/signals/') and request.method == 'POST':
                validate_input_data(body, SignalRequest)
            elif request.url.path == '/api/ml/train-universal':
                validate_input_data(body, TrainUniversalRequest)
            elif request.url.path.startswith('/api/ml/train/'):
                validate_input_data(body, TrainMLRequest)
            elif request.url.path == '/api/demo/settings':
                validate_input_data(body, DemoSettingsRequest)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON format: {str(e)}"
            )

    response = await call_next(request)
    return response


# Security headers middleware
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to responses"""
    response = await call_next(request)

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    return response