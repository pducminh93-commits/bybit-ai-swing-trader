import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import asyncio
from services.bybit_service import BybitService
from models.signal_model import SignalResponse

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'demo_state.json')

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

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'quantity': self.quantity,
            'entry_time': self.entry_time,
            'current_price': self.current_price,
            'unrealized_pnl': self.unrealized_pnl,
            'status': self.status
        }

    @classmethod
    def from_dict(cls, data):
        pos = cls(
            symbol=data['symbol'],
            side=data['side'],
            entry_price=data['entry_price'],
            quantity=data['quantity'],
            timestamp=data['entry_time']
        )
        pos.current_price = data.get('current_price', data['entry_price'])
        pos.unrealized_pnl = data.get('unrealized_pnl', 0.0)
        pos.status = data.get('status', 'OPEN')
        return pos

class DemoTradingService:
    def __init__(self):
        self.capital = 100.0  # USDT
        self.leverage = 1.0  # Leverage multiplier
        self.position_size_pct = 10.0  # Percentage of capital per position
        self.positions: Dict[str, DemoPosition] = {}
        self.history: List[dict] = []
        self.is_running = False
        self.last_signals: Dict[str, SignalResponse] = {}  # Store last signals to compare
        self.load_state()

    def save_state(self):
        """Save demo state to file"""
        state = {
            'capital': self.capital,
            'leverage': self.leverage,
            'position_size_pct': self.position_size_pct,
            'is_running': self.is_running,
            'positions': {k: v.to_dict() for k, v in self.positions.items()},
            'history': self.history
        }
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print(f"Error saving demo state: {e}")

    def load_state(self):
        """Load demo state from file"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                    self.capital = state.get('capital', 100.0)
                    self.leverage = state.get('leverage', 1.0)
                    self.position_size_pct = state.get('position_size_pct', 10.0)
                    self.is_running = state.get('is_running', False)
                    self.history = state.get('history', [])
                    
                    positions_data = state.get('positions', {})
                    self.positions = {k: DemoPosition.from_dict(v) for k, v in positions_data.items()}
            except Exception as e:
                print(f"Error loading demo state: {e}")

    def start_simulation(self):
        """Start the demo trading simulation"""
        self.is_running = True
        # Clear any existing positions when starting
        self.positions.clear()
        self.history.clear()
        self.capital = 100.0  # Reset capital
        self.save_state()

    def stop_simulation(self):
        """Stop the demo trading simulation"""
        self.is_running = False
        self.save_state()

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

    def update_settings(self, capital: Optional[float] = None, leverage: Optional[float] = None, position_size_pct: Optional[float] = None, reset_data: bool = False):
        """Update demo settings"""
        capital_changed = False
        if capital is not None and capital != self.capital:
            self.capital = capital
            capital_changed = True

        if leverage is not None:
            self.leverage = max(1.0, min(100.0, leverage))

        if position_size_pct is not None:
            self.position_size_pct = max(1.0, min(100.0, position_size_pct))

        if reset_data or capital_changed:
            self.positions.clear()
            self.history.clear()
            
        self.save_state()

    def calculate_position_size(self, entry_price: float) -> float:
        """Calculate position size based on percentage of capital and leverage"""
        position_value = self.capital * (self.position_size_pct / 100.0)
        leveraged_value = position_value * self.leverage
        return leveraged_value / entry_price

    def process_signals(self, signals: List[SignalResponse]):
        """Process signals from the signals API"""
        print(f"Demo process_signals called with {len(signals)} signals, is_running: {self.is_running}")

        if not self.is_running:
            print(f"Demo service not running, skipping {len(signals)} signals")
            return

        executed_trades = []
        processed_count = 0
        filtered_count = 0

        for signal in signals:
            processed_count += 1
            print(f"Processing signal: {signal.symbol} {signal.signal} confidence={signal.confidence:.2f}")

            # Only process signals with confidence >= 50% (lowered threshold for testing)
            if signal.confidence >= 0.5:
                result = self.execute_signal(signal)
                if result:
                    executed_trades.append(result)
                    print(f"[SUCCESS] Executed trade for {signal.symbol}: {signal.signal} (confidence: {signal.confidence:.2f})")
                else:
                    print(f"[FAILED] Failed to execute signal for {signal.symbol} (confidence: {signal.confidence:.2f})")
            else:
                filtered_count += 1
                print(f"[FILTERED] Signal for {signal.symbol}: confidence {signal.confidence:.2f} < 0.5")

        print(f"[SUMMARY] Processed {processed_count} signals, executed {len(executed_trades)} trades, filtered {filtered_count} low-confidence signals")

        return executed_trades

    def execute_signal(self, signal: SignalResponse):
        """Execute a trading signal"""
        symbol = signal.symbol
        current_price = self._get_current_price(symbol)

        print(f"Executing signal for {symbol}: {signal.signal}, price: {current_price}")

        if not current_price:
            print(f"No price available for {symbol}")
            return None

        state_changed = False
        result = None

        # Check if we already have a position in this symbol
        if symbol in self.positions and self.positions[symbol].status == 'OPEN':
            existing_pos = self.positions[symbol]
            print(f"Found existing position for {symbol}: {existing_pos.side}")

            # If signal is EXIT or opposite direction, close position
            if signal.signal == 'EXIT' or (signal.signal in ['LONG', 'SHORT'] and signal.signal != existing_pos.side):
                closed_trade = existing_pos.close_position(current_price, datetime.utcnow().isoformat())
                self.history.append(closed_trade)
                del self.positions[symbol]
                result = closed_trade
                state_changed = True
                print(f"Closed existing position for {symbol}")
            else:
                print(f"Keeping existing {existing_pos.side} position for {symbol}")
        else:
            print(f"No existing position for {symbol}")
            # Open new position if signal is LONG or SHORT
            if signal.signal in ['LONG', 'SHORT']:
                entry_price = current_price
                quantity = self.calculate_position_size(entry_price)
                cost = quantity * entry_price
                capital_limit = self.capital * 1.0

                print(f"Opening position: quantity={quantity}, cost={cost}, capital_limit={capital_limit}")

                if cost <= capital_limit:  # Max 100% of capital per position
                    position = DemoPosition(
                        symbol=symbol,
                        side=signal.signal,
                        entry_price=entry_price,
                        quantity=quantity,
                        timestamp=datetime.utcnow().isoformat()
                    )
                    self.positions[symbol] = position
                    result = {
                        'action': 'OPEN',
                        'symbol': symbol,
                        'side': signal.signal,
                        'entry_price': entry_price,
                        'quantity': quantity,
                        'timestamp': position.entry_time
                    }
                    state_changed = True
                    print(f"Position opened successfully for {symbol}")
                else:
                    print(f"Insufficient capital for {symbol}: cost {cost} > limit {capital_limit}")

        if state_changed:
            self.save_state()

        return result

    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        # For demo purposes, return mock prices
        mock_prices = {
            'BTCUSDT': 45000.0,
            'ETHUSDT': 2500.0,
            'SOLUSDT': 100.0,
            'ADAUSDT': 0.5,
            'DOTUSDT': 8.0
        }
        return mock_prices.get(symbol, 100.0)  # Default fallback price

        # TODO: Implement async price fetching for production
        # try:
        #     import asyncio
        #     ticker_data = asyncio.run(BybitService.fetch_tickers())
        #     if ticker_data.get("retCode") == 0:
        #         for ticker in ticker_data["result"]["list"]:
        #             if ticker["symbol"] == symbol:
        #                 return float(ticker["lastPrice"])
        # except Exception as e:
        #     print(f"Error fetching price for {symbol}: {e}")
        # return None

    def update_positions(self):
        """Update all open positions with current prices"""
        if not self.is_running:
            return

        state_changed = False

        for symbol, position in list(self.positions.items()):
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
                            state_changed = True
                        elif current_price >= position.entry_price * 1.05:  # 5% take profit
                            closed_trade = position.close_position(current_price, datetime.utcnow().isoformat())
                            self.history.append(closed_trade)
                            del self.positions[symbol]
                            state_changed = True
                    else:  # SHORT
                        if current_price >= position.entry_price * 1.02:  # 2% stop loss
                            closed_trade = position.close_position(current_price, datetime.utcnow().isoformat())
                            self.history.append(closed_trade)
                            del self.positions[symbol]
                            state_changed = True
                        elif current_price <= position.entry_price * 0.95:  # 5% take profit
                            closed_trade = position.close_position(current_price, datetime.utcnow().isoformat())
                            self.history.append(closed_trade)
                            del self.positions[symbol]
                            state_changed = True

        if state_changed:
            self.save_state()

# Global instance
demo_service = DemoTradingService()