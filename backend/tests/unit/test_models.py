import pytest
from datetime import datetime
from core.models.models import BacktestResult, Trade, Signal, MLModel


class TestBacktestResult:
    """Test BacktestResult model"""

    def test_backtest_result_creation(self):
        """Test creating a BacktestResult instance"""
        backtest = BacktestResult(
            symbol="BTCUSDT",
            strategy_name="Test Strategy",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            initial_balance=1000.0,
            final_balance=1100.0,
            total_return_pct=10.0,
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
            win_rate=0.6,
            profit_factor=1.5,
            max_drawdown_pct=5.0,
            leverage=1.0,
            stop_loss_pct=0.05,
            min_hold_candles=6
        )

        assert backtest.symbol == "BTCUSDT"
        assert backtest.strategy_name == "Test Strategy"
        assert backtest.initial_balance == 1000.0
        assert backtest.final_balance == 1100.0
        assert backtest.total_return_pct == 10.0
        assert backtest.total_trades == 5
        assert backtest.winning_trades == 3
        assert backtest.losing_trades == 2
        assert backtest.win_rate == 0.6
        assert backtest.profit_factor == 1.5
        assert backtest.max_drawdown_pct == 5.0

    def test_backtest_result_to_dict(self):
        """Test converting BacktestResult to dictionary"""
        backtest = BacktestResult(
            id=1,
            symbol="BTCUSDT",
            strategy_name="Test Strategy",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            initial_balance=1000.0,
            final_balance=1100.0,
            total_return_pct=10.0,
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
            win_rate=0.6,
            profit_factor=1.5,
            max_drawdown_pct=5.0,
            leverage=1.0,
            stop_loss_pct=0.05,
            min_hold_candles=6,
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            updated_at=datetime(2024, 1, 1, 10, 0, 0)
        )

        result_dict = backtest.to_dict()

        assert result_dict["id"] == 1
        assert result_dict["symbol"] == "BTCUSDT"
        assert result_dict["total_return_pct"] == 10.0
        assert "created_at" in result_dict
        assert "updated_at" in result_dict


class TestTrade:
    """Test Trade model"""

    def test_trade_creation(self):
        """Test creating a Trade instance"""
        trade = Trade(
            backtest_id=1,
            symbol="BTCUSDT",
            side="LONG",
            entry_time=datetime(2024, 1, 1, 10, 0, 0),
            exit_time=datetime(2024, 1, 2, 10, 0, 0),
            entry_price=50000.0,
            exit_price=51000.0,
            quantity=0.02,
            leverage=1.0,
            realized_pnl=20.0,
            realized_pnl_pct=4.0,
            holding_period=24
        )

        assert trade.symbol == "BTCUSDT"
        assert trade.side == "LONG"
        assert trade.entry_price == 50000.0
        assert trade.exit_price == 51000.0
        assert trade.quantity == 0.02
        assert trade.realized_pnl == 20.0
        assert trade.realized_pnl_pct == 4.0
        assert trade.holding_period == 24

    def test_trade_to_dict(self):
        """Test converting Trade to dictionary"""
        trade = Trade(
            id=1,
            backtest_id=1,
            symbol="BTCUSDT",
            side="LONG",
            entry_time=datetime(2024, 1, 1, 10, 0, 0),
            exit_time=datetime(2024, 1, 2, 10, 0, 0),
            entry_price=50000.0,
            exit_price=51000.0,
            quantity=0.02,
            leverage=1.0,
            realized_pnl=20.0,
            realized_pnl_pct=4.0,
            holding_period=24,
            created_at=datetime(2024, 1, 1, 10, 0, 0)
        )

        result_dict = trade.to_dict()

        assert result_dict["id"] == 1
        assert result_dict["backtest_id"] == 1
        assert result_dict["symbol"] == "BTCUSDT"
        assert result_dict["side"] == "LONG"
        assert result_dict["realized_pnl"] == 20.0
        assert "created_at" in result_dict


class TestSignal:
    """Test Signal model"""

    def test_signal_creation(self):
        """Test creating a Signal instance"""
        signal = Signal(
            symbol="BTCUSDT",
            signal_type="LONG",
            confidence=0.85,
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
            entry_price=50000.0,
            stop_loss=47500.0,
            take_profit=52500.0,
            reason="Strong bullish signal",
            source="live"
        )

        assert signal.symbol == "BTCUSDT"
        assert signal.signal_type == "LONG"
        assert signal.confidence == 0.85
        assert signal.entry_price == 50000.0
        assert signal.stop_loss == 47500.0
        assert signal.take_profit == 52500.0
        assert signal.reason == "Strong bullish signal"
        assert signal.source == "live"

    def test_signal_to_dict(self):
        """Test converting Signal to dictionary"""
        signal = Signal(
            id=1,
            symbol="BTCUSDT",
            signal_type="LONG",
            confidence=0.85,
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
            entry_price=50000.0,
            stop_loss=47500.0,
            take_profit=52500.0,
            reason="Strong bullish signal",
            source="live",
            created_at=datetime(2024, 1, 1, 10, 0, 0)
        )

        result_dict = signal.to_dict()

        assert result_dict["id"] == 1
        assert result_dict["symbol"] == "BTCUSDT"
        assert result_dict["signal_type"] == "LONG"
        assert result_dict["confidence"] == 0.85
        assert result_dict["entry_price"] == 50000.0
        assert result_dict["stop_loss"] == 47500.0
        assert result_dict["take_profit"] == 52500.0
        assert result_dict["reason"] == "Strong bullish signal"
        assert result_dict["source"] == "live"
        assert "created_at" in result_dict


class TestMLModel:
    """Test MLModel model"""

    def test_ml_model_creation(self):
        """Test creating a MLModel instance"""
        model = MLModel(
            name="test_universal_model",
            model_type="universal",
            symbols=["BTCUSDT", "ETHUSDT"],
            accuracy=0.75,
            feature_importance={"rsi_14": 0.3, "macd": 0.25},
            model_path="models/test_model.pkl",
            scaler_path="models/test_scaler.pkl",
            training_samples=1000,
            validation_accuracy=0.72,
            is_active=True,
            version="1.0.0",
            trained_at=datetime(2024, 1, 1, 10, 0, 0)
        )

        assert model.name == "test_universal_model"
        assert model.model_type == "universal"
        assert model.symbols == ["BTCUSDT", "ETHUSDT"]
        assert model.accuracy == 0.75
        assert model.training_samples == 1000
        assert model.is_active == True
        assert model.version == "1.0.0"

    def test_ml_model_to_dict(self):
        """Test converting MLModel to dictionary"""
        model = MLModel(
            id=1,
            name="test_universal_model",
            model_type="universal",
            symbols=["BTCUSDT", "ETHUSDT"],
            accuracy=0.75,
            feature_importance={"rsi_14": 0.3, "macd": 0.25},
            model_path="models/test_model.pkl",
            scaler_path="models/test_scaler.pkl",
            training_samples=1000,
            validation_accuracy=0.72,
            is_active=True,
            version="1.0.0",
            trained_at=datetime(2024, 1, 1, 10, 0, 0),
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            updated_at=datetime(2024, 1, 1, 10, 0, 0)
        )

        result_dict = model.to_dict()

        assert result_dict["id"] == 1
        assert result_dict["name"] == "test_universal_model"
        assert result_dict["model_type"] == "universal"
        assert result_dict["symbols"] == ["BTCUSDT", "ETHUSDT"]
        assert result_dict["accuracy"] == 0.75
        assert result_dict["feature_importance"] == {"rsi_14": 0.3, "macd": 0.25}
        assert result_dict["training_samples"] == 1000
        assert result_dict["is_active"] == True
        assert result_dict["version"] == "1.0.0"
        assert "trained_at" in result_dict
        assert "created_at" in result_dict
        assert "updated_at" in result_dict