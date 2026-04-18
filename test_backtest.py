#!/usr/bin/env python3
"""
Simple test script to run backtest and check for errors
"""
import sys
import os
import logging

# Change to backend directory to match application working directory
os.chdir('backend')

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

try:
    from main import _run_backtest_sync
    print("Starting backtest test...")
    result = _run_backtest_sync('BTCUSDT', 7)
    print("Backtest completed successfully!")
    print(f"Result keys: {list(result.keys())}")
    print(f"Has losing_trades: {'losing_trades' in result}")
    print(f"losing_trades value: {result.get('losing_trades', 'NOT_FOUND')}")
except Exception as e:
    print(f"Error during backtest: {e}")
    import traceback
    traceback.print_exc()