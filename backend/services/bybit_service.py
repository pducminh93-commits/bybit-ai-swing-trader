import requests
from typing import List, Dict, Any

class BybitService:
    BASE_URL = "https://api.bybit.com/v5/market"

    @staticmethod
    def fetch_klines(symbol: str, interval: str = "240", limit: int = 200) -> Dict[str, Any]:
        """Fetch kline data from Bybit"""
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        response = requests.get(f"{BybitService.BASE_URL}/kline", params=params)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def fetch_tickers() -> Dict[str, Any]:
        """Fetch tickers from Bybit"""
        params = {
            "category": "linear"
        }
        response = requests.get(f"{BybitService.BASE_URL}/tickers", params=params)
        response.raise_for_status()
        return response.json()