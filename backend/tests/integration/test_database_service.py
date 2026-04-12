import pytest
from datetime import datetime
from infrastructure.database_service import DatabaseService


@pytest.mark.database
class TestDatabaseService:
    """Test DatabaseService operations"""

    @pytest.mark.asyncio
    async def test_save_and_get_backtest_result(self, sample_backtest_data):
        """Test saving and retrieving backtest results"""
        # Save backtest
        backtest_id = await DatabaseService.save_backtest_result(sample_backtest_data, "BTCUSDT")
        assert backtest_id > 0

        # Get backtest by ID
        backtest = await DatabaseService.get_backtest_by_id(backtest_id)
        assert backtest is not None
        assert backtest["symbol"] == "BTCUSDT"
        assert backtest["total_return_pct"] == 10.0
        assert backtest["total_trades"] == 5
        assert backtest["win_rate"] == 0.6
        assert len(backtest["trades"]) == 1

        # Check trade data
        trade = backtest["trades"][0]
        assert trade["symbol"] == "BTCUSDT"
        assert trade["side"] == "LONG"
        assert trade["realized_pnl"] == 20.0
        assert trade["realized_pnl_pct"] == 4.0

    @pytest.mark.asyncio
    async def test_get_backtest_results(self, sample_backtest_data):
        """Test getting multiple backtest results"""
        # Save multiple backtests
        await DatabaseService.save_backtest_result(sample_backtest_data, "BTCUSDT")
        await DatabaseService.save_backtest_result(sample_backtest_data, "ETHUSDT")

        # Get all backtests
        backtests = await DatabaseService.get_backtest_results()
        assert len(backtests) >= 2

        # Get BTCUSDT backtests only
        btc_backtests = await DatabaseService.get_backtest_results("BTCUSDT")
        assert len(btc_backtests) >= 1
        assert all(b["symbol"] == "BTCUSDT" for b in btc_backtests)

    @pytest.mark.asyncio
    async def test_save_and_get_signals(self, sample_signal_data):
        """Test saving and retrieving signals"""
        # Save signal
        signal_id = await DatabaseService.save_signal(sample_signal_data)
        assert signal_id > 0

        # Get recent signals
        signals = await DatabaseService.get_signals()
        assert len(signals) >= 1

        # Find our signal
        our_signal = next((s for s in signals if s["id"] == signal_id), None)
        assert our_signal is not None
        assert our_signal["symbol"] == "BTCUSDT"
        assert our_signal["signal_type"] == "LONG"
        assert our_signal["confidence"] == 0.85
        assert our_signal["source"] == "live"

    @pytest.mark.asyncio
    async def test_save_and_get_ml_model(self, sample_ml_model_data):
        """Test saving and retrieving ML models"""
        # Save ML model
        model_id = await DatabaseService.save_ml_model(sample_ml_model_data)
        assert model_id > 0

        # Get all models
        models = await DatabaseService.get_ml_models()
        assert len(models) >= 1

        # Find our model
        our_model = next((m for m in models if m["id"] == model_id), None)
        assert our_model is not None
        assert our_model["name"] == "test_universal_model"
        assert our_model["model_type"] == "universal"
        assert our_model["accuracy"] == 0.75
        assert our_model["is_active"] == True
        assert our_model["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test getting database statistics"""
        stats = await DatabaseService.get_statistics()

        assert "total_backtests" in stats
        assert "total_trades" in stats
        assert "total_signals" in stats
        assert "recent_performance" in stats

        assert isinstance(stats["total_backtests"], int)
        assert isinstance(stats["total_trades"], int)
        assert isinstance(stats["total_signals"], int)
        assert isinstance(stats["recent_performance"], dict)

    @pytest.mark.asyncio
    async def test_get_signals_by_symbol_and_time(self, sample_signal_data):
        """Test filtering signals by symbol and time"""
        # Save signals
        await DatabaseService.save_signal(sample_signal_data)

        # Modify signal for different symbol
        eth_signal = sample_signal_data.copy()
        eth_signal["symbol"] = "ETHUSDT"
        await DatabaseService.save_signal(eth_signal)

        # Get all signals
        all_signals = await DatabaseService.get_signals()
        assert len(all_signals) >= 2

        # Get BTC signals only
        btc_signals = await DatabaseService.get_signals("BTCUSDT")
        assert len(btc_signals) >= 1
        assert all(s["symbol"] == "BTCUSDT" for s in btc_signals)

        # Get signals from last 24 hours
        recent_signals = await DatabaseService.get_signals(hours=24)
        assert len(recent_signals) >= 2

    @pytest.mark.asyncio
    async def test_get_nonexistent_backtest(self):
        """Test getting non-existent backtest returns None"""
        result = await DatabaseService.get_backtest_by_id(99999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_active_ml_models(self, sample_ml_model_data):
        """Test getting only active ML models"""
        # Save active model
        active_model = sample_ml_model_data.copy()
        active_model["is_active"] = True
        await DatabaseService.save_ml_model(active_model)

        # Save inactive model
        inactive_model = sample_ml_model_data.copy()
        inactive_model["name"] = "inactive_model"
        inactive_model["is_active"] = False
        await DatabaseService.save_ml_model(inactive_model)

        # Get all models
        all_models = await DatabaseService.get_ml_models()
        assert len(all_models) >= 2

        # Get active models only
        active_models = await DatabaseService.get_ml_models(active_only=True)
        assert len(active_models) >= 1
        assert all(m["is_active"] == True for m in active_models)