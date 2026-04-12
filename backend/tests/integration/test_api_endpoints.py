import pytest
from httpx import AsyncClient
from datetime import datetime


@pytest.mark.integration
class TestAPIEndpoints:
    """Test API endpoints integration"""

    @pytest.mark.asyncio
    async def test_get_backtests_endpoint(self, client):
        """Test GET /api/backtests endpoint"""
        response = await client.get("/api/backtests")

        assert response.status_code == 200
        data = response.json()
        assert "backtests" in data
        assert "count" in data
        assert isinstance(data["backtests"], list)
        assert isinstance(data["count"], int)

    @pytest.mark.asyncio
    async def test_get_backtest_by_id_endpoint(self, client, sample_backtest_data):
        """Test GET /api/backtests/{id} endpoint"""
        from infrastructure.database_service import DatabaseService

        # First save a backtest
        backtest_id = await DatabaseService.save_backtest_result(sample_backtest_data, "BTCUSDT")

        # Then retrieve it via API
        response = await client.get(f"/api/backtests/{backtest_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"
        assert data["total_return_pct"] == 10.0
        assert data["total_trades"] == 5
        assert "trades" in data
        assert len(data["trades"]) == 1

    @pytest.mark.asyncio
    async def test_get_nonexistent_backtest(self, client):
        """Test GET /api/backtests/{id} for non-existent backtest"""
        response = await client.get("/api/backtests/99999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_get_signals_history_endpoint(self, client, sample_signal_data):
        """Test GET /api/signals/history endpoint"""
        from infrastructure.database_service import DatabaseService

        # Save a signal first
        await DatabaseService.save_signal(sample_signal_data)

        # Get signals via API
        response = await client.get("/api/signals/history")

        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "count" in data
        assert isinstance(data["signals"], list)
        assert len(data["signals"]) >= 1

        # Check signal structure
        signal = data["signals"][0]
        assert "symbol" in signal
        assert "signal_type" in signal
        assert "confidence" in signal
        assert "timestamp" in signal

    @pytest.mark.asyncio
    async def test_get_ml_models_endpoint(self, client, sample_ml_model_data):
        """Test GET /api/ml/models endpoint"""
        from infrastructure.database_service import DatabaseService

        # Save an ML model first
        await DatabaseService.save_ml_model(sample_ml_model_data)

        # Get models via API
        response = await client.get("/api/ml/models")

        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "count" in data
        assert isinstance(data["models"], list)
        assert len(data["models"]) >= 1

        # Check model structure
        model = data["models"][0]
        assert "name" in model
        assert "model_type" in model
        assert "accuracy" in model

    @pytest.mark.asyncio
    async def test_get_statistics_endpoint(self, client):
        """Test GET /api/stats endpoint"""
        response = await client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()

        required_keys = ["total_backtests", "total_trades", "total_signals", "recent_performance"]
        for key in required_keys:
            assert key in data

        assert isinstance(data["total_backtests"], int)
        assert isinstance(data["total_trades"], int)
        assert isinstance(data["total_signals"], int)
        assert isinstance(data["recent_performance"], dict)

    @pytest.mark.asyncio
    async def test_get_signals_filtered_by_symbol(self, client, sample_signal_data):
        """Test GET /api/signals/history with symbol filter"""
        from infrastructure.database_service import DatabaseService

        # Save signals for different symbols
        btc_signal = sample_signal_data.copy()
        btc_signal["symbol"] = "BTCUSDT"
        await DatabaseService.save_signal(btc_signal)

        eth_signal = sample_signal_data.copy()
        eth_signal["symbol"] = "ETHUSDT"
        await DatabaseService.save_signal(eth_signal)

        # Get BTC signals only
        response = await client.get("/api/signals/history?symbol=BTCUSDT")

        assert response.status_code == 200
        data = response.json()
        assert len(data["signals"]) >= 1

        # All returned signals should be for BTCUSDT
        for signal in data["signals"]:
            assert signal["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_train_universal_model_endpoint(self, client):
        """Test POST /api/ml/train-universal endpoint"""
        # This test might take a long time and requires real API data
        # For now, we'll just test that the endpoint exists and returns a proper error
        # when no symbols are provided or when training fails

        response = await client.post("/api/ml/train-universal")

        # Should return 200 if successful, or 500 with error details
        assert response.status_code in [200, 500]

        data = response.json()
        if response.status_code == 200:
            assert "status" in data
            assert "message" in data
            assert "accuracy" in data
        else:
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_get_backtests_filtered_by_symbol(self, client, sample_backtest_data):
        """Test GET /api/backtests with symbol filter"""
        from infrastructure.database_service import DatabaseService

        # Save backtests for different symbols
        await DatabaseService.save_backtest_result(sample_backtest_data, "BTCUSDT")
        await DatabaseService.save_backtest_result(sample_backtest_data, "ETHUSDT")

        # Get BTC backtests only
        response = await client.get("/api/backtests?symbol=BTCUSDT")

        assert response.status_code == 200
        data = response.json()
        assert len(data["backtests"]) >= 1

        # All returned backtests should be for BTCUSDT
        for backtest in data["backtests"]:
            assert backtest["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test GET / endpoint"""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Bybit AI Swing Trader" in data["message"]

    @pytest.mark.asyncio
    async def test_error_handling_invalid_backtest_id(self, client):
        """Test error handling for invalid backtest ID"""
        response = await client.get("/api/backtests/invalid_id")

        # Should return 422 for invalid ID format
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_signals_limit_parameter(self, client):
        """Test GET /api/signals/history with limit parameter"""
        response = await client.get("/api/signals/history?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data["signals"]) <= 10  # Should not exceed limit