import pytest
from services.backtester import Backtester

def test_backtester_initialization():
    bt = Backtester(initial_balance=1000, leverage=5.0)
    assert bt.initial_balance == 1000
    assert bt.leverage == 5.0
    assert bt.balance == 1000
    assert bt.position == 0

def test_backtester_reset():
    bt = Backtester()
    bt.balance = 2000
    bt.position = 1
    bt.reset()
    assert bt.balance == bt.initial_balance
    assert bt.position == 0

def test_calculate_metrics_no_trades():
    bt = Backtester()
    metrics = bt._calculate_metrics()
    assert metrics['total_trades'] == 0

def test_run_backtest():
    bt = Backtester()
    signals = [
        {'timestamp': '1772524800000', 'signal': 'LONG', 'confidence': 0.6, 'reason': 'Test'},
    ]
    prices = [
        {'timestamp': '1772524800000', 'close': 67000},
        {'timestamp': '1775822400000', 'close': 72814},
    ]
    result = bt.run_backtest(signals, prices)
    assert 'trades' in result
    assert 'final_balance' in result
    assert result['final_balance'] > 10000  # Should have profit