# Bybit AI Swing Trader

AI-powered swing trading system for Bybit cryptocurrency exchange. Combines technical analysis, machine learning, and advanced backtesting for automated trading signals.

## Features

### 🤖 AI & Machine Learning
- Multi-timeframe technical analysis (1h, 4h, 1d)
- ML models: Random Forest, Gradient Boosting, LSTM
- Ensemble methods for improved accuracy
- Universal model training across multiple symbols

### 📊 Technical Analysis
- 20+ indicators (RSI, MACD, Bollinger Bands, etc.)
- Candlestick pattern recognition
- Fibonacci retracements
- Volume analysis

### 📈 Backtesting & Risk Management
- Historical backtesting with performance metrics
- Stop-loss, leverage, and position sizing
- Sharpe/Sortino ratios, max drawdown
- Walk-forward validation

### 🔧 Developer-Friendly
- FastAPI backend with auto-generated docs
- React/TypeScript frontend
- Docker support
- Comprehensive logging and error handling

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-repo/bybit-ai-swing-trader.git
   cd bybit-ai-swing-trader
   ```

2. **Start the backend server**
   ```bash
   cd backend

   # Windows
   start_server.bat

   # Linux/Mac
   chmod +x start_server.sh
   ./start_server.sh

   # Or manually:
   pip install -r requirements.txt
   python init_db.py
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Start the frontend (in a new terminal)**
   ```bash
   cd frontend
   npm install
   npm start
   ```

4. **Access the app**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Troubleshooting

### "Failed to load market data"
This error occurs when the frontend cannot connect to the backend server.

**Solution:**
1. Ensure the backend server is running on port 8000
2. Check that no firewall is blocking the connection
3. Verify the backend logs for any startup errors

### Backend server won't start
**Check:**
1. Python 3.8+ is installed
2. All dependencies are installed: `pip install -r requirements.txt`
3. Database is initialized: `python init_db.py`

### Frontend won't start
**Check:**
1. Node.js is installed
2. Dependencies are installed: `npm install`
   - API Docs: http://localhost:8000/docs

## Architecture

```
├── backend/           # Python FastAPI backend
│   ├── services/      # Business logic
│   ├── models/        # ML models and data models
│   └── main.py        # API endpoints
├── frontend/          # React/TypeScript UI
├── docker/            # Docker configuration
└── docs/              # Documentation
```

## API Examples

### Get Trading Signals
```bash
curl "http://localhost:8000/api/signals/BTCUSDT"
```

### Run Backtest
```bash
curl -X POST "http://localhost:8000/api/backtest/BTCUSDT?days=30&leverage=10"
```

### Train ML Model
```bash
curl -X POST "http://localhost:8000/api/ml/train-universal?symbols=BTCUSDT,ETHUSDT"
```

## Configuration

- **Capital**: Default 100 USDT
- **Leverage**: Default 10x
- **Stop Loss**: 5%
- **Min Hold Time**: 24 hours (6 candles)

## Development

### Backend
```bash
cd backend
pip install -r requirements.txt
pytest  # Run tests
mypy .  # Type checking
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Performance Metrics

- Win Rate
- Profit Factor
- Sharpe/Sortino Ratio
- Maximum Drawdown
- Total Return

## Risk Disclaimer

This software is for educational and research purposes. Trading cryptocurrencies involves significant risk of loss. Always test strategies thoroughly and never risk more than you can afford to lose.

## License

MIT License - see LICENSE file for details.