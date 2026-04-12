import pytest
import asyncio
from typing import AsyncGenerator
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.config import db
from main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db():
    """Create test database session."""
    # Use in-memory SQLite for tests
    test_db_url = "sqlite+aiosqlite:///:memory:"

    # Override the database URL for testing
    original_url = db.engine.url
    db.engine = db.engine.__class__(test_db_url)

    # Create tables
    async with db.engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.create_all)

    yield db

    # Cleanup
    async with db.engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.drop_all)


@pytest.fixture
async def db_session(test_db) -> AsyncGenerator[AsyncSession, None]:
    """Get database session for each test."""
    async with test_db.async_session() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Get HTTP client for testing FastAPI app."""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def sample_backtest_data():
    """Sample backtest data for testing."""
    return {
        "symbol": "BTCUSDT",
        "strategy_name": "Test Strategy",
        "start_date": "2024-01-01T00:00:00",
        "end_date": "2024-01-31T23:59:59",
        "initial_balance": 1000.0,
        "final_balance": 1100.0,
        "total_return_pct": 10.0,
        "total_trades": 5,
        "winning_trades": 3,
        "losing_trades": 2,
        "win_rate": 0.6,
        "profit_factor": 1.5,
        "max_drawdown_pct": 5.0,
        "sharpe_ratio": 1.2,
        "leverage": 1.0,
        "stop_loss_pct": 0.05,
        "min_hold_candles": 6,
        "trades": [
            {
                "symbol": "BTCUSDT",
                "side": "LONG",
                "entry_time": "2024-01-01T10:00:00",
                "exit_time": "2024-01-02T10:00:00",
                "entry_price": 50000.0,
                "exit_price": 51000.0,
                "quantity": 0.02,
                "leverage": 1.0,
                "realized_pnl": 20.0,
                "realized_pnl_pct": 4.0,
                "holding_period": 24,
                "stop_loss_price": 47500.0,
                "take_profit_price": 52500.0
            }
        ]
    }


@pytest.fixture
def sample_signal_data():
    """Sample signal data for testing."""
    return {
        "symbol": "BTCUSDT",
        "signal": "LONG",
        "confidence": 0.85,
        "timestamp": "2024-01-01T10:00:00",
        "entry_price": 50000.0,
        "stop_loss": 47500.0,
        "take_profit": 52500.0,
        "reason": "Strong bullish signal",
        "indicators": {
            "rsi_14": 65.0,
            "macd": 100.0,
            "atr_14": 500.0
        },
        "source": "live"
    }


@pytest.fixture
def sample_ml_model_data():
    """Sample ML model data for testing."""
    return {
        "name": "test_universal_model",
        "model_type": "universal",
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "accuracy": 0.75,
        "feature_importance": {"rsi_14": 0.3, "macd": 0.25},
        "model_path": "models/test_model.pkl",
        "scaler_path": "models/test_scaler.pkl",
        "training_samples": 1000,
        "validation_accuracy": 0.72,
        "is_active": True,
        "version": "1.0.0"
    }