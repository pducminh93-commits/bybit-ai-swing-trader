from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any
from core.logging.config import get_logger

logger = get_logger("exceptions")

class BybitTraderException(Exception):
    """Base exception for Bybit Trader application"""

    def __init__(self, message: str, status_code: int = 500, details: Dict[str, Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(BybitTraderException):
    """Validation error"""
    def __init__(self, message: str, field: str = None):
        super().__init__(message, 400, {"field": field} if field else {})

class DatabaseError(BybitTraderException):
    """Database operation error"""
    def __init__(self, message: str, operation: str = None):
        super().__init__(message, 500, {"operation": operation} if operation else {})

class APIError(BybitTraderException):
    """External API error"""
    def __init__(self, message: str, service: str = None, status_code: int = None):
        super().__init__(message, 502, {
            "service": service,
            "api_status_code": status_code
        } if service or status_code else {})

class MLModelError(BybitTraderException):
    """ML model operation error"""
    def __init__(self, message: str, model_type: str = None):
        super().__init__(message, 500, {"model_type": model_type} if model_type else {})

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for FastAPI"""

    # Log the exception
    logger.error(f"Unhandled exception in {request.method} {request.url.path}: {str(exc)}", exc_info=True)

    # Handle different exception types
    if isinstance(exc, BybitTraderException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": exc.__class__.__name__,
                    "message": exc.message,
                    "details": exc.details
                }
            }
        )
    elif isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "HTTPException",
                    "message": exc.detail
                }
            }
        )
    else:
        # Generic exception
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "InternalServerError",
                    "message": "An unexpected error occurred"
                }
            }
        )

def log_request_middleware(request: Request, call_next):
    """Middleware to log requests"""
    logger.info(f"Request: {request.method} {request.url.path}")

    try:
        response = call_next(request)
        logger.info(f"Response: {response.status_code} for {request.method} {request.url.path}")
        return response
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url.path} - {str(e)}")
        raise