import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import time
import json
import os
import logging
import structlog
from services.database import DatabaseManager

# Setup structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

class Backtester:
    def __init__(self, initial_balance: float = 100, commission: float = 0.001, leverage: float = 10.0,
                 min_hold_candles: int = 6, stop_loss_pct: float = 0.05, max_position_pct: float = 1.0):
        """
        Initialize backtester with enhanced parameters
        initial_balance: Starting balance in USD
        commission: Trading fee per trade (0.001 = 0.1%)
        leverage: Leverage for futures trading (1.0 = spot)
        min_hold_candles: Minimum candles to hold position before allowing opposite signal
        stop_loss_pct: Stop loss percentage (0.05 = 5%)
        max_position_pct: Maximum position size as percentage of capital (1.0 = 100%)
        """
        self.initial_balance = initial_balance
        self.commission = commission
        self.leverage = leverage
        self.min_hold_candles = min_hold_candles
        self.stop_loss_pct = stop_loss_pct
        self.max_position_pct = max_position_pct
        self.reset()

    def reset(self):
        """Reset backtester state for a new run"""
        self.balance = self.initial_balance
        self.equity = self.initial_balance  # Track equity curve
        self.position = 0.0  # position size: positive long, negative short, 0 none
        self.entry_price = 0.0
        self.entry_time = None  # Will store datetime object
        self.current_position = None  # Current position object
        self.trades = []
        self.equity_curve = []
        self.current_time = None
        self.last_open_candle = -self.min_hold_candles  # To allow first trade
        self.walk_forward_results = []  # For walk-forward validation
        self.position_sizing_method = 'fixed'  # 'fixed', 'kelly', 'volatility'

        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_fees = 0.0
        self.peak_balance = self.initial_balance
        self.max_drawdown = 0.0

    def _calculate_position_size(self, entry_price: float) -> float:
        """
        Calculate position size based on current balance and risk parameters
        Returns the quantity to trade
        """
        if entry_price <= 0:
            return 0.0

        # Maximum position value based on balance and max_position_pct
        max_position_value = self.balance * self.max_position_pct

        # Account for leverage
        effective_balance = self.balance * self.leverage

        # Position size = (effective_balance * max_position_pct) / entry_price
        position_size = (effective_balance * self.max_position_pct) / entry_price

        # Ensure we don't exceed available balance after fees
        estimated_fee = position_size * entry_price * self.commission
        max_position_with_fees = (self.balance - estimated_fee) * self.leverage / entry_price

        return min(position_size, max_position_with_fees)

    def calculate_pnl(self, entry_price: float, exit_price: float, quantity: float) -> Tuple[float, float]:
        """
        Calculate realized PnL and percentage return for a trade
        Returns (pnl, pnl_pct)
        """
        if self.position > 0:  # Long position
            pnl = (exit_price - entry_price) * abs(quantity)
        else:  # Short position
            pnl = (entry_price - exit_price) * abs(quantity)

        pnl_pct = (pnl / (entry_price * abs(quantity))) * 100 if entry_price > 0 else 0.0
        return pnl, pnl_pct

    def update_equity_curve(self, timestamp: datetime):
        """Update equity curve with current balance"""
        self.equity_curve.append({
            'timestamp': timestamp,
            'balance': self.balance,
            'equity': self.equity
        })

        # Update drawdown tracking
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance

        current_drawdown = (self.peak_balance - self.balance) / self.peak_balance
        self.max_drawdown = max(self.max_drawdown, current_drawdown)

    def run_backtest(self, signals_data: List[Dict[str, Any]], price_data: List[Dict[str, Any]], symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """
        Run enhanced backtest on signals and price data
        Returns comprehensive results with detailed metrics
        """
        logger.info(f"Starting enhanced backtest for {symbol} with {len(signals_data)} signals and {len(price_data)} price points")
        self.reset()

        # Create efficient price lookup
        price_lookup = {d['timestamp']: d['close'] for d in price_data}

        # Process each signal
        for idx, signal in enumerate(signals_data):
            timestamp = signal['timestamp']
            price = price_lookup.get(timestamp)

            if price is None:
                continue

            self.current_time = timestamp

            # Convert timestamp to datetime safely
            try:
                ts_seconds = int(timestamp) / 1000
                self.current_datetime = datetime.utcfromtimestamp(ts_seconds)
            except (ValueError, OverflowError, OSError) as e:
                logger.warning(f"Invalid timestamp {timestamp}, using current time: {e}")
                self.current_datetime = datetime.utcnow()

            signal_type = signal['signal']
            confidence = signal.get('confidence', 0.0)

            # Execute signal if confidence meets threshold
            if confidence >= 0.4:  # Lower threshold for more trades
                self._execute_signal_enhanced(signal_type, price, self.current_datetime, signal, idx, symbol)

            # Apply stop loss logic
            self._apply_stop_loss(price, self.current_datetime, symbol)

            # Update equity curve
            self.update_equity_curve(self.current_datetime)

        # Close any remaining positions at the end
        self._close_remaining_positions(price_data, symbol)

        # Calculate comprehensive metrics
        return self._calculate_enhanced_metrics()

    def _close_position(self, price: float, timestamp: datetime, reason: str, symbol: str):
        """Close current position"""
        if self.position == 0:
            return

        if self.position > 0:  # Close long
            profit = (price - self.entry_price) * self.position
            profit_after_fee = profit * (1 - self.commission)
            self.balance += profit_after_fee
            self.trades.append({
                'symbol': symbol,
                'side': 'LONG',
                'entry_time': self.entry_time,
                'exit_time': timestamp,
                'entry_price': self.entry_price,
                'exit_price': price,
                'quantity': self.position,
                'leverage': self.leverage,
                'realized_pnl': profit_after_fee,
                'realized_pnl_pct': (price - self.entry_price) / self.entry_price * 100,
                'holding_period': 1,  # placeholder
                'entry_reason': '',  # placeholder
                'exit_reason': reason
            })
        else:  # Close short
            profit = (self.entry_price - price) * (-self.position)
            profit_after_fee = profit * (1 - self.commission)
            self.balance += profit_after_fee
            self.trades.append({
                'symbol': symbol,
                'side': 'SHORT',
                'entry_time': self.entry_time,
                'exit_time': timestamp,
                'entry_price': self.entry_price,
                'exit_price': price,
                'quantity': -self.position,
                'leverage': self.leverage,
                'realized_pnl': profit_after_fee,
                'realized_pnl_pct': (self.entry_price - price) / self.entry_price * 100,
                'holding_period': 1,  # placeholder
                'entry_reason': '',  # placeholder
                'exit_reason': reason
            })

        self.position = 0
        self.entry_price = 0
        self.entry_time = None

    def _execute_signal(self, signal: str, price: float, timestamp: datetime, signal_data: Dict[str, Any], candle_idx: int, symbol: str):
        """Execute buy/sell signal"""
        # Hỗ trợ cả BUY/SELL và LONG/SHORT
        normalized_signal = 'LONG' if signal in ['BUY', 'LONG'] else ('SHORT' if signal in ['SELL', 'SHORT'] else signal)

        if normalized_signal == 'LONG' and self.position <= 0:
            # Check min hold time for opposite position
            if self.position < 0 and candle_idx - self.last_open_candle < self.min_hold_candles:
                return  # Skip signal to prevent flip

            # Close short position if any
            if self.position < 0:
                profit = (self.entry_price - price) * abs(self.position)  # Short profit
                profit_after_fee = profit * (1 - self.commission)
                self.balance += profit_after_fee

                self.trades.append({
                    'symbol': symbol,
                    'side': 'SHORT',
                    'entry_time': self.entry_time,
                    'exit_time': timestamp,
                    'entry_price': self.entry_price,
                    'exit_price': price,
                    'quantity': -self.position,
                    'leverage': self.leverage,
                    'realized_pnl': profit_after_fee,
                    'realized_pnl_pct': (self.entry_price - price) / self.entry_price * 100,
                    'holding_period': 1,
                    'entry_reason': '',
                    'exit_reason': 'Signal change to BUY'
                })

            # Open long position
            position_size = (self.balance * self.leverage) / price * (1 - self.commission)
            self.position = position_size  # Store actual size
            self.entry_price = price
            self.entry_time = self.current_datetime  # Store datetime object
            self.balance -= position_size * price * self.commission  # Fee
            self.last_open_candle = candle_idx

        elif normalized_signal == 'SHORT' and self.position >= 0:
            # Check min hold time for opposite position
            if self.position > 0 and candle_idx - self.last_open_candle < self.min_hold_candles:
                return  # Skip signal to prevent flip

            # Close long position if any
            if self.position > 0:
                profit = (price - self.entry_price) * abs(self.position)  # Long profit
                profit_after_fee = profit * (1 - self.commission)
                self.balance += profit_after_fee

                self.trades.append({
                    'symbol': symbol,
                    'side': 'LONG',
                    'entry_time': self.entry_time,
                    'exit_time': timestamp,
                    'entry_price': self.entry_price,
                    'exit_price': price,
                    'quantity': self.position,
                    'leverage': self.leverage,
                    'realized_pnl': profit_after_fee,
                    'realized_pnl_pct': (price - self.entry_price) / self.entry_price * 100,
                    'holding_period': 1,
                    'entry_reason': '',
                    'exit_reason': 'Signal change to SELL'
                })

            # Open short position
            position_size = (self.balance * self.leverage) / price * (1 - self.commission)
            self.position = -position_size  # Store actual size
            self.entry_price = price
            self.entry_time = self.current_datetime  # Store datetime object
            self.balance -= position_size * price * self.commission  # Fee
            self.last_open_candle = candle_idx

        elif signal == 'EXIT' and self.position != 0:
            # Close any open position
            self._close_position(price, timestamp, 'EXIT signal', symbol)

    def walk_forward_validation(self, signals_data: List[Dict[str, Any]], price_data: List[Dict[str, Any]],
                              window_size: int = 100, step_size: int = 20) -> Dict[str, Any]:
        """
        Perform walk-forward validation by training/testing on sliding windows.
        """
        results = []
        n_points = len(signals_data)

        for start in range(0, n_points - window_size, step_size):
            end = start + window_size
            if end >= n_points:
                break

            # Train window
            train_signals = signals_data[start:end]
            train_prices = price_data[start:end]

            # Test window (next step_size points)
            test_start = end
            test_end = min(end + step_size, n_points)
            test_signals = signals_data[test_start:test_end]
            test_prices = price_data[test_start:test_end]

            # Run backtest on test window
            self.reset()
            test_result = self.run_backtest(test_signals, test_prices)

            results.append({
                'train_window': {'start': start, 'end': end},
                'test_window': {'start': test_start, 'end': test_end},
                'metrics': test_result['metrics'],
                'total_return': test_result['total_return']
            })

        # Aggregate results
        total_returns = [r['total_return'] for r in results]
        win_rates = [r['metrics']['win_rate'] for r in results]

        return {
            'walk_forward_results': results,
            'average_return': np.mean(total_returns),
            'return_std': np.std(total_returns),
            'average_win_rate': np.mean(win_rates),
            'sharpe_ratio': np.mean(total_returns) / np.std(total_returns) if np.std(total_returns) > 0 else 0,
            'total_windows': len(results)
        }

    def kelly_position_size(self, win_rate: float, win_loss_ratio: float) -> float:
        """
        Calculate Kelly Criterion position size.
        Kelly % = (bp - q) / b
        where b = odds (avg_win / avg_loss), p = win_rate, q = 1-p
        """
        if win_rate <= 0 or win_rate >= 1 or win_loss_ratio <= 0:
            return 0.01  # Default 1%

        b = win_loss_ratio
        kelly = (win_rate * b - (1 - win_rate)) / b

        # Half Kelly for safety
        return max(0.005, min(kelly * 0.5, 0.1))  # Between 0.5% and 10%

    def calculate_position_size(self, capital: float, risk_pct: float = 0.02) -> float:
        """
        Calculate position size based on method.
        For now, return fixed percentage, but can extend to Kelly.
        """
        if self.position_sizing_method == 'kelly':
            # Need historical data to calculate win_rate and win_loss_ratio
            # Placeholder: use fixed for now
            return capital * risk_pct
        elif self.position_sizing_method == 'volatility':
            # ATR-based sizing
            return capital * risk_pct
        else:
            # Fixed percentage
            return capital * risk_pct

    def _execute_signal_enhanced(self, signal_type: str, price: float, timestamp: datetime, signal: Dict[str, Any], candle_idx: int, symbol: str):
        """Enhanced signal execution with better position management"""
        # Check if we can open a new position
        if self.position != 0:
            # Check if signal allows position change
            if self._can_change_position(signal_type, candle_idx):
                # Close existing position first
                self._close_position(price, timestamp, f'Opposite signal ({signal_type})', symbol)

        # Open new position if we have no position
        if self.position == 0 and signal_type in ['LONG', 'SHORT']:
            self._open_position(signal_type, price, timestamp, signal, symbol)

    def _apply_stop_loss(self, current_price: float, timestamp: datetime, symbol: str):
        """Apply stop loss logic"""
        if self.position == 0 or self.entry_price == 0:
            return

        if self.position > 0:  # Long position
            loss_pct = (self.entry_price - current_price) / self.entry_price
        else:  # Short position
            loss_pct = (current_price - self.entry_price) / self.entry_price

        if loss_pct >= self.stop_loss_pct:
            self._close_position(current_price, timestamp, 'Stop Loss', symbol)

    def _can_change_position(self, signal_type: str, candle_idx: int) -> bool:
        """Check if we can change position based on minimum hold time"""
        if self.last_open_candle < 0:
            return True
        return (candle_idx - self.last_open_candle) >= self.min_hold_candles

    def _open_position(self, signal_type: str, price: float, timestamp: datetime, signal: Dict[str, Any], symbol: str):
        """Open a new position with enhanced sizing"""
        position_size = self._calculate_position_size(price)

        if position_size <= 0:
            return

        # Apply commission for opening
        entry_fee = position_size * price * self.commission
        self.balance -= entry_fee
        self.total_fees += entry_fee

        # Set position
        self.position = position_size if signal_type == 'LONG' else -position_size
        self.entry_price = price
        self.entry_time = timestamp
        self.last_open_candle = signal.get('candle_idx', 0)

        logger.info(f"Opened {signal_type} position: size={position_size:.6f}, price={price:.2f}, fee={entry_fee:.4f}")

    def _close_remaining_positions(self, price_data: List[Dict[str, Any]], symbol: str):
        """Close any remaining positions at the end of backtest"""
        if self.position == 0 or not price_data:
            return

        last_price_data = price_data[-1]
        last_price = last_price_data['close']

        try:
            ts_seconds = int(last_price_data['timestamp']) / 1000
            last_datetime = datetime.utcfromtimestamp(ts_seconds)
        except (ValueError, OverflowError, OSError):
            last_datetime = datetime.utcnow()

        self._close_position(last_price, last_datetime, 'End of Backtest', symbol)

    def _calculate_enhanced_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_profit': 0.0,
                'avg_profit_per_trade': 0.0,
                'max_profit': 0.0,
                'max_loss': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'max_drawdown': 0.0,
                'profit_factor': 0.0,
                'total_fees': 0.0,
                'net_return': 0.0
            }

        # Basic trade statistics
        total_trades = len(self.trades)
        winning_trades = self.winning_trades
        losing_trades = self.losing_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        # PnL analysis
        pnls = [trade['realized_pnl'] for trade in self.trades]
        total_profit = sum(pnls)
        avg_profit_per_trade = total_profit / total_trades
        max_profit = max(pnls) if pnls else 0.0
        max_loss = min(pnls) if pnls else 0.0

        # Profit factor
        gross_profit = sum(pnl for pnl in pnls if pnl > 0)
        gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Risk metrics
        returns = []
        if len(self.equity_curve) > 1:
            prev_equity = self.initial_balance
            for point in self.equity_curve:
                current_equity = point['equity']
                if prev_equity > 0:
                    ret = (current_equity - prev_equity) / prev_equity
                    returns.append(ret)
                prev_equity = current_equity

        # Sharpe and Sortino ratios (simplified)
        if returns:
            avg_return = sum(returns) / len(returns)
            std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe_ratio = (avg_return / std_return * (365 ** 0.5)) if std_return > 0 else 0.0

            # Sortino ratio (downside deviation)
            downside_returns = [r for r in returns if r < 0]
            if downside_returns:
                downside_std = (sum(r ** 2 for r in downside_returns) / len(downside_returns)) ** 0.5
                sortino_ratio = (avg_return / downside_std * (365 ** 0.5)) if downside_std > 0 else 0.0
            else:
                sortino_ratio = float('inf')
        else:
            sharpe_ratio = 0.0
            sortino_ratio = 0.0

        # Net return calculation
        net_return = ((self.balance - self.initial_balance) / self.initial_balance * 100) if self.initial_balance > 0 else 0.0

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit_per_trade': avg_profit_per_trade,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': self.max_drawdown * 100,  # Convert to percentage
            'profit_factor': profit_factor,
            'total_fees': self.total_fees,
            'net_return': net_return,
            'final_balance': self.balance,
            'total_return_pct': (self.balance - self.initial_balance) / self.initial_balance * 100
        }

    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics"""
        logger.info(f"_calculate_metrics called with {len(self.trades)} trades")

        if not self.trades:
            logger.warning("No trades to calculate metrics")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_profit': 0,
                'avg_profit_per_trade': 0,
                'max_profit': 0,
                'max_loss': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'max_drawdown': 0,
                'profit_factor': 0
            }

        # Basic metrics
        total_trades = len(self.trades)
        logger.info(f"Total trades: {total_trades}")

        winning_trades = len([t for t in self.trades if t.get('realized_pnl', 0) > 0])
        losing_trades = len([t for t in self.trades if t.get('realized_pnl', 0) < 0])
        logger.info(f"Winning trades: {winning_trades}, Losing trades: {losing_trades}")

        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        logger.info(f"Win rate: {win_rate}")

        # Profit metrics
        profits = [t.get('realized_pnl', 0) for t in self.trades]
        total_profit = sum(profits)
        avg_profit = np.mean(profits) if profits else 0
        max_profit = max(profits) if profits else 0
        max_loss = min(profits) if profits else 0

        # Risk metrics
        if profits:
            profit_std = np.std(profits)
            sharpe_ratio = avg_profit / profit_std if profit_std > 0 else 0

            # Sortino ratio (only downside deviation)
            negative_profits = [p for p in profits if p < 0]
            downside_std = np.std(negative_profits) if negative_profits else 0
            sortino_ratio = avg_profit / downside_std if downside_std > 0 else 0

            # Maximum drawdown
            equity_values = [point['equity'] for point in self.equity_curve]
            peak = equity_values[0]
            max_dd = 0
            for equity in equity_values:
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak * 100
                max_dd = max(max_dd, dd)
        else:
            sharpe_ratio = 0
            sortino_ratio = 0
            max_dd = 0

        result_metrics = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit_per_trade': avg_profit,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_dd,
            'profit_factor': abs(sum([p for p in profits if p > 0]) / sum([p for p in profits if p < 0])) if sum([p for p in profits if p < 0]) != 0 else 'inf'
        }

        logger.info(f"Returning metrics: {result_metrics}")
        return result_metrics

    def save_results(self, results: Dict[str, Any], filename: str):
        """Save backtest results to file"""
        os.makedirs('backtests', exist_ok=True)

        # Convert numpy types to native Python types
        def convert_numpy(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_numpy(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            else:
                return obj

        results_converted = convert_numpy(results)

        with open(f'backtests/{filename}.json', 'w') as f:
            json.dump(results_converted, f, indent=2, default=str)

    @staticmethod
    def load_results(filename: str) -> Dict[str, Any]:
        """Load backtest results from file"""
        with open(f'backtests/{filename}.json', 'r') as f:
            return json.load(f)