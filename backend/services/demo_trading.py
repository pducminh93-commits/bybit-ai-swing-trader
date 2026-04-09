from datetime import datetime
from typing import List, Dict, Optional
import asyncio
from services.bybit_service import BybitService
from models.signal_model import SignalResponse

class DemoPosition:
    def __init__(self, symbol: str, side: str, entry_price: float, quantity: float, timestamp: str):
        self.symbol = symbol
        self.side = side  # 'LONG' or 'SHORT'
        self.entry_price = entry_price
        self.quantity = quantity
        self.entry_time = timestamp
        self.current_price = entry_price
        self.unrealized_pnl = 0.0
        self.status = 'OPEN'

    def update_price(self, current_price: float):
        self.current_price = current_price
        if self.side == 'LONG':
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity

    def close_position(self, exit_price: float, exit_time: str) -> dict:
        self.current_price = exit_price
        if self.side == 'LONG':
            realized_pnl = (exit_price - self.entry_price) * self.quantity
        else:  # SHORT
            realized_pnl = (self.entry_price - exit_price) * self.quantity

        return {
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'exit_price': exit_price,
            'quantity': self.quantity,
            'entry_time': self.entry_time,
            'exit_time': exit_time,
            'realized_pnl': realized_pnl,
            'pnl_percentage': (realized_pnl / (self.entry_price * self.quantity)) * 100
        }

class DemoTradingService:
    def __init__(self):
        self.capital = 100.0  # USDT
        self.positions: Dict[str, DemoPosition] = {}
        self.history: List[dict] = []
        self.is_running = False
        self.last_signals: Dict[str, SignalResponse] = {}  # Store last signals to compare

    def start_simulation(self):
        """Start the demo trading simulation"""
        self.is_running = True

    def stop_simulation(self):
        """Stop the demo trading simulation"""
        self.is_running = False

    def get_balance(self) -> float:
        """Get current balance (capital + unrealized P&L)"""
        total_unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        return self.capital + total_unrealized

    def get_open_positions(self) -> List[dict]:
        """Get all open positions"""
        return [
            {
                'symbol': pos.symbol,
                'side': pos.side,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'quantity': pos.quantity,
                'entry_time': pos.entry_time,
                'unrealized_pnl': pos.unrealized_pnl,
                'pnl_percentage': (pos.unrealized_pnl / (pos.entry_price * pos.quantity)) * 100
            }
            for pos in self.positions.values()
            if pos.status == 'OPEN'
        ]

    def get_trade_history(self) -> List[dict]:
        """Get trade history"""
        return self.history.copy()

    def calculate_position_size(self, entry_price: float) -> float:
        """Calculate position size based on 10% risk per trade"""
        risk_amount = self.capital * 0.1  # 10% of capital
        # Assume 2% stop loss for position sizing
        stop_loss_pct = 0.02
        position_value = risk_amount / stop_loss_pct
        return position_value / entry_price

    def process_signals(self, signals: List[SignalResponse]):
        """Process signals from the signals API"""
        if not self.is_running:
            return

        executed_trades = []

        for signal in signals:
            # Only process signals with confidence >= 60%
            if signal.confidence >= 0.6:
                result = self.execute_signal(signal)
                if result:
                    executed_trades.append(result)

        return executed_trades

    def execute_signal(self, signal: SignalResponse):
        """Execute a trading signal"""
        symbol = signal.symbol
        current_price = self._get_current_price(symbol)

        if not current_price:
            return None

        # Check if we already have a position in this symbol
        if symbol in self.positions and self.positions[symbol].status == 'OPEN':
            existing_pos = self.positions[symbol]

            # If signal is EXIT or opposite direction, close position
            if signal.signal == 'EXIT' or (signal.signal in ['LONG', 'SHORT'] and signal.signal != existing_pos.side):
                closed_trade = existing_pos.close_position(current_price, datetime.utcnow().isoformat())
                self.history.append(closed_trade)
                del self.positions[symbol]
                return closed_trade
        else:
            # Open new position if signal is LONG or SHORT
            if signal.signal in ['LONG', 'SHORT']:
                entry_price = current_price
                quantity = self.calculate_position_size(entry_price)
                if quantity * entry_price <= self.capital * 0.5:  # Max 50% of capital per position
                    position = DemoPosition(
                        symbol=symbol,
                        side=signal.signal,
                        entry_price=entry_price,
                        quantity=quantity,
                        timestamp=datetime.utcnow().isoformat()
                    )
                    self.positions[symbol] = position
                    return {
                        'action': 'OPEN',
                        'symbol': symbol,
                        'side': signal.signal,
                        'entry_price': entry_price,
                        'quantity': quantity,
                        'timestamp': position.entry_time
                    }

        return None

    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        try:
            ticker_data = BybitService.fetch_tickers()
            if ticker_data.get("retCode") == 0:
                for ticker in ticker_data["result"]["list"]:
                    if ticker["symbol"] == symbol:
                        return float(ticker["lastPrice"])
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
        return None

    def update_positions(self):
        """Update all open positions with current prices"""
        if not self.is_running:
            return

        for symbol, position in self.positions.items():
            if position.status == 'OPEN':
                current_price = self._get_current_price(symbol)
                if current_price:
                    position.update_price(current_price)

                    # Check for stop loss / take profit (simple implementation)
                    if position.side == 'LONG':
                        if current_price <= position.entry_price * 0.98:  # 2% stop loss
                            closed_trade = position.close_position(current_price, datetime.utcnow().isoformat())
                            self.history.append(closed_trade)
                            del self.positions[symbol]
                        elif current_price >= position.entry_price * 1.05:  # 5% take profit
                            closed_trade = position.close_position(current_price, datetime.utcnow().isoformat())
                            self.history.append(closed_trade)
                            del self.positions[symbol]
                    else:  # SHORT
                        if current_price >= position.entry_price * 1.02:  # 2% stop loss
                            closed_trade = position.close_position(current_price, datetime.utcnow().isoformat())
                            self.history.append(closed_trade)
                            del self.positions[symbol]
                        elif current_price <= position.entry_price * 0.95:  # 5% take profit
                            closed_trade = position.close_position(current_price, datetime.utcnow().isoformat())
                            self.history.append(closed_trade)
                            del self.positions[symbol]

# Global instance
demo_service = DemoTradingService()