# Bybit AI Swing Trader Backend - Enhanced Edition

Backend Python nâng cao sử dụng FastAPI để cung cấp AI phân tích kỹ thuật mạnh mẽ cho swing trading trên Bybit, tích hợp Machine Learning và Backtesting.

## 🚀 New Features (v2.0)

### 🤖 Advanced AI & ML
- **Multi-Timeframe Analysis**: Phân tích đồng thời 1h, 4h, 1d với weighted aggregation
- **Machine Learning Models**: Random Forest, Gradient Boosting, LSTM cho signal prediction
- **Deep Learning**: Neural Networks cho pattern recognition
- **Ensemble Methods**: Kết hợp multiple models để tăng accuracy

### 📊 Enhanced Technical Analysis
- **Advanced Indicators**: ADX, Williams %R, CCI, MFI, Ichimoku Cloud, OBV
- **Candlestick Patterns**: Hammer, Shooting Star, Engulfing, Doji, Marubozu detection
- **Fibonacci Retracements**: Tự động tính các mức Fibonacci support/resistance
- **Volume Analysis**: Chaikin Money Flow, On Balance Volume

### 📈 Risk Management & Backtesting
- **Advanced Risk Metrics**: Sharpe Ratio, Sortino Ratio, Maximum Drawdown
- **Portfolio Optimization**: Modern Portfolio Theory implementation
- **Backtesting Framework**: Historical validation với detailed performance metrics
- **Walk-Forward Optimization**: Adaptive parameter optimization

### 🔧 Developer Features
- **Model Persistence**: Auto-save/load trained ML models
- **Performance Monitoring**: Real-time metrics tracking
- **API Rate Limiting**: Built-in rate limiting cho production use
- **Error Handling**: Comprehensive error handling và logging

## Installation

1. Tạo virtual environment:
```bash
python -m venv venv
```

2. Activate venv:
```bash
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Unix
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API sẽ available tại http://localhost:8000

## API Endpoints

### Core Trading
- `GET /api/bybit/kline?symbol=BTCUSDT&interval=240&limit=200` - Lấy dữ liệu kline
- `GET /api/bybit/tickers` - Lấy danh sách tickers
- `GET /api/signals/{symbol}?use_multiframe=true` - Lấy tín hiệu với multi-timeframe analysis
- `GET /api/signals?symbols=BTCUSDT,ETHUSDT` - Lấy tín hiệu cho nhiều symbols

### Machine Learning
- `POST /api/ml/train/{symbol}?model_type=rf` - Train ML model (rf/gb/ensemble)
- `GET /api/ml/predict/{symbol}?model_type=rf` - ML-based signal prediction

### Backtesting
- `POST /api/backtest/{symbol}?days=30` - Run backtest on historical data
- Results saved to `backtests/` directory với performance metrics

## Architecture

- `services/bybit_service.py` - Xử lý API Bybit
- `services/ta_analysis.py` - Phân tích kỹ thuật nâng cao với TA-Lib
- `services/ai_model.py` - Rule-based AI signal generation
- `services/ml_model.py` - Machine Learning models (RF, GB, LSTM)
- `services/multi_timeframe.py` - Multi-timeframe analysis
- `services/backtester.py` - Backtesting framework với risk metrics
- `models/signal_model.py` - Pydantic models
- `main.py` - FastAPI app chính

## Performance Metrics

Backtester tính toán:
- Win Rate, Profit Factor
- Sharpe/Sortino Ratios
- Maximum Drawdown
- Risk-adjusted returns
- Trade-by-trade analysis

## Model Training

```python
# Train ML model
POST /api/ml/train/BTCUSDT?model_type=rf

# Model saved as: models/BTCUSDT_rf_model.pkl
# Feature importance available in response
```

## Backtesting Example

```python
# Run 30-day backtest
POST /api/backtest/BTCUSDT?days=30

# Returns detailed performance metrics
{
  "total_return": 15.2,
  "win_rate": 0.68,
  "sharpe_ratio": 1.23,
  "max_drawdown": 8.5,
  "total_trades": 45
}
```

## Future Enhancements

- [ ] **Sentiment Analysis**: Twitter/News integration
- [ ] **Reinforcement Learning**: Dynamic strategy adaptation
- [ ] **Portfolio Optimization**: MPT-based asset allocation
- [ ] **Live Trading**: Direct Bybit API integration
- [ ] **WebSocket Streaming**: Real-time signal updates