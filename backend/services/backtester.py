import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import os

class Backtester:
    def __init__(self, initial_balance: float = 10000, commission: float = 0.001):
        """
        Initialize backtester
        initial_balance: Starting balance in USD
        commission: Trading fee (0.001 = 0.1%)
        """
        self.initial_balance = initial_balance
        self.commission = commission
        self.reset()

    def reset(self):
        """Reset backtester state"""
        self.balance = self.initial_balance
        self.position = 0  # 0: no position, 1: long, -1: short
        self.entry_price = 0
        self.trades = []
        self.equity_curve = []
        self.current_time = None

    def run_backtest(self, signals_data: List[Dict[str, Any]], price_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run backtest on signals and price data"""
        self.reset()

        # Create price lookup by timestamp
        price_lookup = {d['timestamp']: d['close'] for d in price_data}

        for signal in signals_data:
            timestamp = signal['timestamp']
            price = price_lookup.get(timestamp)

            if price is None:
                continue

            self.current_time = timestamp
            signal_type = signal['signal']
            confidence = signal.get('confidence', 0)

            # Execute signal if confidence > threshold
            if confidence > 0.6:
                self._execute_signal(signal_type, price, timestamp, signal)

            # Update equity curve
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': self.balance + (self.position * price if self.position != 0 else 0)
            })

        # Calculate performance metrics
        metrics = self._calculate_metrics()

        return {
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'final_balance': self.balance,
            'total_return': (self.balance - self.initial_balance) / self.initial_balance * 100,
            'metrics': metrics
        }

    def _execute_signal(self, signal: str, price: float, timestamp: str, signal_data: Dict[str, Any]):
        """Execute buy/sell signal"""
        if signal == 'BUY' and self.position <= 0:
            # Close short position if any
            if self.position == -1:
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
            position_size = self.balance / price * (1 - self.commission)
            self.position = 1
            self.entry_price = price
            self.balance -= position_size * price * self.commission  # Fee

            self.trades.append({
                'type': 'BUY',
                'price': price,
                'size': position_size,
                'timestamp': timestamp,
                'reason': signal_data.get('reason', '')
            })

        elif signal == 'SELL' and self.position >= 0:
            # Close long position if any
            if self.position == 1:
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
            position_size = self.balance / price * (1 - self.commission)
            self.position = -1
            self.entry_price = price
            self.balance -= position_size * price * self.commission  # Fee

            self.trades.append({
                'type': 'SELL',
                'price': price,
                'size': position_size,
                'timestamp': timestamp,
                'reason': signal_data.get('reason', '')
            })

    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics"""
        if not self.trades:
            return {'total_trades': 0}

        # Basic metrics
        total_trades = len([t for t in self.trades if t['type'] in ['BUY', 'SELL']])
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
            'profit_factor': abs(sum([p for p in profits if p > 0]) / sum([p for p in profits if p < 0])) if sum([p for p in profits if p < 0]) != 0 else float('inf')
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