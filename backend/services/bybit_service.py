import asyncio
import httpx
from aiocache import cached
from typing import List, Dict, Any

class BybitService:
    BASE_URL = "https://api.bybit.com/v5/market"

    @staticmethod
    @cached(ttl=300)  # Cache for 5 minutes
    async def fetch_klines(symbol: str, interval: str = "240", limit: int = 200) -> Dict[str, Any]:
        """Fetch kline (OHLCV) data from Bybit asynchronously"""
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BybitService.BASE_URL}/kline", params=params)
            response.raise_for_status()
            return response.json()

    @staticmethod
    @cached(ttl=60)  # Cache for 1 minute
    async def fetch_tickers() -> Dict[str, Any]:
        """Fetch current tickers from Bybit asynchronously"""
        params = {
            "category": "linear"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BybitService.BASE_URL}/tickers", params=params)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def fetch_open_interest(symbol: str, intervalTime: str = "4h", limit: int = 50) -> Dict[str, Any]:
        """
        Fetch Open Interest history from Bybit
        intervalTime: 5min, 15min, 30min, 1h, 4h, 1d
        """
        params = {
            "category": "linear",
            "symbol": symbol,
            "intervalTime": intervalTime,
            "limit": limit
        }
        response = requests.get(f"{BybitService.BASE_URL}/open-interest", params=params)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def fetch_funding_rate_history(symbol: str, limit: int = 50) -> Dict[str, Any]:
        """
        Fetch historical funding rate from Bybit
        """
        params = {
            "category": "linear",
            "symbol": symbol,
            "limit": limit
        }
        response = requests.get(f"{BybitService.BASE_URL}/funding/history", params=params)
        response.raise_for_status()
        return response.json()