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

## Project Structure

```
.
├── backend/                 # Python FastAPI backend
│   ├── main.py              # Main API application
│   ├── bybit_trader.db      # SQLite database
│   ├── demo_state.json      # Demo mode state
│   ├── logs/                # Application logs
│   │   └── bybit_trader.json
│   ├── models/              # ML models and data models
│   │   ├── universal_ensemble_model.pkl
│   │   ├── universal_ensemble_scaler.pkl
│   │   └── backups/         # Model backups
│   │       └── *.pkl
│   └── services/            # Business logic services
│       └── *.py
├── frontend/                # React/TypeScript UI
│   └── tsconfig.tsbuildinfo # TypeScript build info
├── models/                  # Additional models
│   └── BTCUSDT_rf_model.pkl
├── logs/                    # Logs directory
│   └── bybit_trader.json
├── bybit_trader.db          # Additional database file
├── check_db.py              # Database check script
├── force_recreate_db.py     # Force recreate database
├── recreate_db.py           # Recreate database
├── test_backtest.py         # Backtest testing script
└── README.md                # This file
```

## Proposed Improvements for CFA-Level Analysis

Dựa trên cấu trúc dự án hiện tại và các tiêu chuẩn phân tích tài chính chuyên nghiệp (CFA), dưới đây là tổng hợp các điểm cần cải thiện để nâng cấp hệ thống Bybit AI Swing Trader từ một công cụ hỗ trợ kỹ thuật thành một hệ thống đầu tư có tư duy quản trị:

### 1. Cải thiện về Logic Dữ liệu (Feature Engineering)
Dữ liệu đầu vào quyết định 80% độ chính xác của Model. Hiện tại bạn đang dùng nến OHLC thuần túy, cần nâng cấp:
- **Xử lý tính dừng (Stationarity)**: Chuyển đổi giá đóng cửa sang Log Returns hoặc sử dụng Fractional Differentiation để giữ lại giá trị lịch sử mà vẫn đảm bảo tính dừng.
- **Đặc trưng vĩ mô**: Tích hợp các biến số như Chỉ số sức mạnh đồng USD (DXY) và lợi suất trái phiếu chính phủ.
- **Dữ liệu On-chain**: Thêm các chỉ số như tỷ lệ nạp/rút lên sàn của cá mập (Exchange Flow) để làm tín hiệu cảnh báo sớm.

### 2. Bổ sung các Model chuyên biệt (Architectural Upgrade)
Đừng chỉ dựa vào Random Forest hay LSTM đơn lẻ, hãy xây dựng hệ thống phân lớp:
- **HMM (Hidden Markov Model)**: Xác định "Trạng thái thị trường" (Market Regime). AI cần biết thị trường đang ở giai đoạn: Tăng trưởng ổn định, Biến động mạnh, hay Sideway.
- **GARCH Model**: Dự báo độ biến động (Volatility). Đây là cốt lõi của CFA để tính toán Stop-loss động.
- **Sentiment Analysis**: Một mô hình NLP nhỏ để theo dõi tâm lý đám đông qua tin tức hoặc chỉ số Fear & Greed.

### 3. Nâng cấp Quản trị rủi ro (Risk Management - CFA Level III)
Đây là điểm khác biệt lớn nhất giữa một Trader nghiệp dư và một quỹ đầu tư:
- **Dynamic Position Sizing**: Thay đổi khối lượng lệnh dựa trên biến động thị trường (ATR-based) và số dư khả dụng.
- **Monte Carlo Simulation**: Tích hợp vào Backtesting để giả lập hàng ngàn kịch bản xấu nhất (Black Swan).
- **Tính toán VaR (Value at Risk)**: AI phải trả lời được câu hỏi: "Với độ tin cậy 95%, số tiền tối đa tôi có thể mất trong 24 giờ tới là bao nhiêu?"

### 4. Tối ưu hóa Backtesting (Validation)
Tránh hiện tượng "học vẹt" (Overfitting):
- **Walk-forward Optimization**: Thay vì test trên một khoảng thời gian cố định, hãy dùng cơ chế cửa sổ trượt.
- **Phân tích Chi phí cơ hội**: So sánh hiệu quả của AI với chiến lược Buy & Hold BTC thông qua chỉ số Information Ratio.

### 5. Cấu trúc Hệ thống (Infrastructure)
- **Unit Testing cho Logic Tài chính**: Viết test case cho các hàm tính toán Sharpe Ratio, Drawdown.
- **Fail-safe Mechanism**: Bổ sung cơ chế ngắt mạch (Circuit Breaker). Nếu AI thua lỗ vượt quá một ngưỡng nhất định trong ngày, hệ thống phải tự động đóng toàn bộ vị thế.

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