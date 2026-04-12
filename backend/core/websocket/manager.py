from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime
from core.logging.config import get_logger
from infrastructure.database_service import DatabaseService
from services.signal_integrator import AdvancedSignalIntegrator

logger = get_logger("websocket")

class WebSocketManager:
    """WebSocket connection manager for real-time trading signals"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.signal_integrators: Dict[str, AdvancedSignalIntegrator] = {}
        self.is_streaming = False

    async def connect(self, websocket: WebSocket, symbol: str):
        """Connect a WebSocket client for a specific symbol"""
        await websocket.accept()

        if symbol not in self.active_connections:
            self.active_connections[symbol] = set()

        self.active_connections[symbol].add(websocket)

        # Initialize signal integrator for this symbol if not exists
        if symbol not in self.signal_integrators:
            self.signal_integrators[symbol] = AdvancedSignalIntegrator(symbol)

        logger.info(f"WebSocket client connected for {symbol}. Total connections: {len(self.active_connections[symbol])}")

        # Send welcome message
        await websocket.send_json({
            "type": "connection_established",
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Connected to {symbol} signal stream"
        })

    def disconnect(self, websocket: WebSocket, symbol: str):
        """Disconnect a WebSocket client"""
        if symbol in self.active_connections:
            self.active_connections[symbol].discard(websocket)
            logger.info(f"WebSocket client disconnected from {symbol}. Remaining connections: {len(self.active_connections[symbol])}")

            # Clean up empty symbol connections
            if not self.active_connections[symbol]:
                del self.active_connections[symbol]
                if symbol in self.signal_integrators:
                    del self.signal_integrators[symbol]

    async def broadcast_signal(self, symbol: str, signal_data: Dict):
        """Broadcast signal to all connected clients for a symbol"""
        if symbol not in self.active_connections:
            return

        message = {
            "type": "signal_update",
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "data": signal_data
        }

        disconnected_clients = set()

        for websocket in self.active_connections[symbol]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send signal to client: {e}")
                disconnected_clients.add(websocket)

        # Remove disconnected clients
        for client in disconnected_clients:
            self.disconnect(client, symbol)

    async def broadcast_market_data(self, symbol: str, market_data: Dict):
        """Broadcast market data updates"""
        if symbol not in self.active_connections:
            return

        message = {
            "type": "market_data",
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "data": market_data
        }

        disconnected_clients = set()

        for websocket in self.active_connections[symbol]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send market data to client: {e}")
                disconnected_clients.add(websocket)

        # Remove disconnected clients
        for client in disconnected_clients:
            self.disconnect(client, symbol)

    async def start_signal_streaming(self):
        """Start real-time signal streaming"""
        if self.is_streaming:
            return

        self.is_streaming = True
        logger.info("Starting real-time signal streaming...")

        while self.is_streaming:
            try:
                # Generate signals for all active symbols
                for symbol in list(self.active_connections.keys()):
                    if symbol in self.signal_integrators:
                        integrator = self.signal_integrators[symbol]

                        # Generate signal
                        signal_result = integrator.generate_actionable_signal()

                        if signal_result.get("status") == "success":
                            await self.broadcast_signal(symbol, signal_result)

                            # Save signal to database
                            try:
                                signal_data = {
                                    "symbol": symbol,
                                    "signal": signal_result.get("trade_decision", {}).get("signal", "HOLD"),
                                    "confidence": signal_result.get("ai_confidence", 0.5),
                                    "timestamp": signal_result.get("timestamp"),
                                    "entry_price": signal_result.get("latest_price"),
                                    "stop_loss": signal_result.get("trade_decision", {}).get("stop_loss"),
                                    "take_profit": signal_result.get("trade_decision", {}).get("take_profit"),
                                    "reason": f"Real-time signal: {signal_result.get('raw_signal', 'HOLD')}",
                                    "indicators": signal_result.get("features", {}),
                                    "source": "websocket"
                                }
                                await DatabaseService.save_signal(signal_data)
                            except Exception as e:
                                logger.warning(f"Failed to save WebSocket signal to database: {e}")

                # Wait before next signal generation (30 seconds)
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in signal streaming: {e}")
                await asyncio.sleep(5)  # Wait before retry

    async def stop_signal_streaming(self):
        """Stop real-time signal streaming"""
        self.is_streaming = False
        logger.info("Stopped real-time signal streaming")

    def get_connection_stats(self) -> Dict:
        """Get connection statistics"""
        return {
            "total_symbols": len(self.active_connections),
            "total_connections": sum(len(connections) for connections in self.active_connections.values()),
            "symbols": list(self.active_connections.keys()),
            "connections_per_symbol": {symbol: len(connections) for symbol, connections in self.active_connections.items()},
            "is_streaming": self.is_streaming
        }

    async def send_personal_message(self, websocket: WebSocket, message: Dict):
        """Send a personal message to a specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")

# Global WebSocket manager instance
websocket_manager = WebSocketManager()