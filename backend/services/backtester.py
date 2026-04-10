import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Backtester:
    def __init__(self, initial_balance: float = 100, commission: float = 0.001, leverage: float = 10.0, min_hold_candles: int = 6, stop_loss_pct: float = 0.05):
        """
        Initialize backtester
        initial_balance: Starting balance in USD
        commission: Trading fee (0.001 = 0.1%)
        leverage: Leverage for futures trading (1.0 = spot)
        min_hold_candles: Minimum candles to hold position before allowing opposite signal (6 = 24h for 4h candles)
        stop_loss_pct: Stop loss percentage (0.05 = 5%)
        """
        self.initial_balance = initial_balance
        self.commission = commission
        self.leverage = leverage
        self.min_hold_candles = min_hold_candles
        self.stop_loss_pct = stop_loss_pct
        self.reset()

    def reset(self):
        """Reset backtester state"""
        self.balance = self.initial_balance
        self.position = 0  # position size: positive long, negative short, 0 none
        self.entry_price = 0
        self.trades = []
        self.equity_curve = []
        self.current_time = None
        self.last_open_candle = -self.min_hold_candles  # To allow first trade

    def run_backtest(self, signals_data: List[Dict[str, Any]], price_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.info(f"Starting backtest with {len(signals_data)} signals and {len(price_data)} price points")
        """Run backtest on signals and price data"""
        self.reset()

        # Create price lookup by timestamp
        price_lookup = {d['timestamp']: d['close'] for d in price_data}

        for idx, signal in enumerate(signals_data):
            timestamp = signal['timestamp']
            price = price_lookup.get(timestamp)

            if price is None:
                continue

            self.current_time = timestamp
            signal_type = signal['signal']
            confidence = signal.get('confidence', 0)

            # Execute signal if confidence > threshold
            if confidence > 0.4:
                self._execute_signal(signal_type, price, timestamp, signal, idx)

            # Update equity curve
            position_value = abs(self.position) * price if self.position != 0 else 0
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': self.balance + position_value
            })

            # Check stop loss
            if self.position != 0:
                if self.position > 0:  # Long position
                    loss_pct = (self.entry_price - price) / self.entry_price
                else:  # Short position
                    loss_pct = (price - self.entry_price) / self.entry_price
                if loss_pct >= self.stop_loss_pct:
                    self._close_position(price, timestamp, 'Stop Loss')

        # Đóng toàn bộ lệnh đang mở ở cây nến cuối cùng để tính toán PnL thực tế
        if self.position != 0 and len(price_data) > 0:
            last_timestamp = price_data[-1]['timestamp']
            last_price = price_data[-1]['close']
            
            if self.position == 1:
                profit = (last_price - self.entry_price) * abs(self.position)
                profit_after_fee = profit * (1 - self.commission)
                self.balance += profit_after_fee
                self.trades.append({
                    'type': 'CLOSE_LONG',
                    'entry_price': self.entry_price,
                    'exit_price': last_price,
                    'profit': profit_after_fee,
                    'timestamp': last_timestamp,
                    'reason': 'End of Backtest'
                })
            elif self.position == -1:
                profit = (self.entry_price - last_price) * abs(self.position)
                profit_after_fee = profit * (1 - self.commission)
                self.balance += profit_after_fee
                self.trades.append({
                    'type': 'CLOSE_SHORT',
                    'entry_price': self.entry_price,
                    'exit_price': last_price,
                    'profit': profit_after_fee,
                    'timestamp': last_timestamp,
                    'reason': 'End of Backtest'
                })
            self.position = 0

        # Calculate performance metrics
        metrics = self._calculate_metrics()

        return {
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'final_balance': self.balance,
            'total_return': (self.balance - self.initial_balance) / self.initial_balance * 100,
            'metrics': metrics
        }

    def _close_position(self, price: float, timestamp: str, reason: str):
        """Close current position"""
        if self.position == 0:
            return

        if self.position > 0:  # Close long
            profit = (price - self.entry_price) * self.position
            profit_after_fee = profit * (1 - self.commission)
            self.balance += profit_after_fee
            self.trades.append({
                'type': 'CLOSE_LONG',
                'entry_price': self.entry_price,
                'exit_price': price,
                'profit': profit_after_fee,
                'timestamp': timestamp,
                'reason': reason
            })
        else:  # Close short
            profit = (self.entry_price - price) * (-self.position)
            profit_after_fee = profit * (1 - self.commission)
            self.balance += profit_after_fee
            self.trades.append({
                'type': 'CLOSE_SHORT',
                'entry_price': self.entry_price,
                'exit_price': price,
                'profit': profit_after_fee,
                'timestamp': timestamp,
                'reason': reason
            })

        self.position = 0
        self.entry_price = 0

    def _execute_signal(self, signal: str, price: float, timestamp: str, signal_data: Dict[str, Any], candle_idx: int):
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
                    'type': 'CLOSE_SHORT',
                    'entry_price': self.entry_price,
                    'exit_price': price,
                    'profit': profit_after_fee,
                    'timestamp': timestamp,
                    'reason': 'Signal change to BUY'
                })

            # Open long position
            position_size = (self.balance * self.leverage) / price * (1 - self.commission)
            self.position = position_size  # Store actual size
            self.entry_price = price
            self.balance -= position_size * price * self.commission  # Fee

            self.trades.append({
                'type': 'LONG',
                'price': price,
                'size': position_size,
                'timestamp': timestamp,
                'reason': signal_data.get('reason', '')
            })
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
                    'type': 'CLOSE_LONG',
                    'entry_price': self.entry_price,
                    'exit_price': price,
                    'profit': profit_after_fee,
                    'timestamp': timestamp,
                    'reason': 'Signal change to SELL'
                })

            # Open short position
            position_size = (self.balance * self.leverage) / price * (1 - self.commission)
            self.position = -position_size  # Store actual size
            self.entry_price = price
            self.balance -= position_size * price * self.commission  # Fee

            self.trades.append({
                'type': 'SHORT',
                'price': price,
                'size': position_size,
                'timestamp': timestamp,
                'reason': signal_data.get('reason', '')
            })
            self.last_open_candle = candle_idx

        elif signal == 'EXIT' and self.position != 0:
            # Close any open position
            if self.position == 1:  # Close long
                profit = (price - self.entry_price) * abs(self.position)
                profit_after_fee = profit * (1 - self.commission)
                self.balance += profit_after_fee

                self.trades.append({
                    'type': 'CLOSE_LONG',
                    'entry_price': self.entry_price,
                    'exit_price': price,
                    'profit': profit_after_fee,
                    'timestamp': timestamp,
                    'reason': 'EXIT signal'
                })
            elif self.position == -1:  # Close short
                profit = (self.entry_price - price) * abs(self.position)
                profit_after_fee = profit * (1 - self.commission)
                self.balance += profit_after_fee

                self.trades.append({
                    'type': 'CLOSE_SHORT',
                    'entry_price': self.entry_price,
                    'exit_price': price,
                    'profit': profit_after_fee,
                    'timestamp': timestamp,
                    'reason': 'EXIT signal'
                })

            self.position = 0
            self.entry_price = 0

    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics"""
        if not self.trades:
            logger.warning("No trades to calculate metrics")
            return {'total_trades': 0}
        """Calculate performance metrics"""
        if not self.trades:
            return {'total_trades': 0}

        # Basic metrics
        total_trades = len([t for t in self.trades if t['type'] in ['BUY', 'SELL', 'LONG', 'SHORT']])
        winning_trades = len([t for t in self.trades if t.get('profit', 0) > 0])
        losing_trades = len([t for t in self.trades if t.get('profit', 0) < 0])

        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # Profit metrics
        profits = [t.get('profit', 0) for t in self.trades if 'profit' in t]
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

        return {
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