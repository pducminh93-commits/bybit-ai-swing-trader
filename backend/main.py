import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services.bybit_service import BybitService
from services.ta_analysis import TechnicalAnalysis
from services.ai_model import AISignalGenerator
from services.multi_timeframe import MultiTimeframeAnalysis
from services.ml_model import MLSignalPredictor
from services.backtester import Backtester
from models.signal_model import SignalResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Bybit AI Swing Trader Backend", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class KlineResponse(BaseModel):
    startTime: str
    open: str
    high: str
    low: str
    close: str
    volume: str
    turnover: str

@app.get("/api/bybit/kline")
async def get_kline(
    symbol: str = "BTCUSDT",
    interval: str = "240",
    limit: int = 200
) -> dict:
    try:
        data = BybitService.fetch_klines(symbol, interval, limit)
        if data.get("retCode") != 0:
            raise HTTPException(status_code=400, detail=data.get("retMsg", "Failed to fetch klines"))
        return data
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Bybit API error: {str(e)}")

@app.get("/api/bybit/tickers")
async def get_tickers() -> dict:
    try:
        data = BybitService.fetch_tickers()
        if data.get("retCode") != 0:
            raise HTTPException(status_code=400, detail=data.get("retMsg", "Failed to fetch tickers"))
        return data
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Bybit API error: {str(e)}")

@app.get("/api/signals/{symbol}")
async def get_signal(symbol: str, use_multiframe: bool = True) -> SignalResponse:
    try:
        if use_multiframe:
            # Use multi-timeframe analysis
            mtf_analysis = MultiTimeframeAnalysis(symbol)
            mtf_results = mtf_analysis.analyze_all_timeframes()
            aggregated_signal = mtf_analysis.get_aggregated_signal()

            # Get detailed indicators from 4h timeframe
            if '4h' in mtf_results:
                indicators = mtf_results['4h']['indicators']
                current_price = mtf_results['4h']['current_price']
            else:
                # Fallback to single timeframe
                kline_data = BybitService.fetch_klines(symbol, interval="240", limit=200)
                if kline_data.get("retCode") != 0:
                    raise HTTPException(status_code=400, detail=kline_data.get("retMsg", "Failed to fetch klines"))
                klines = kline_data["result"]["list"]
                ta = TechnicalAnalysis(klines)
                indicators = ta.calculate_indicators()
                current_price = ta.get_latest_price()

            # Calculate TP/SL using AI generator
            ai_generator = AISignalGenerator()
            tp_sl = ai_generator.calculate_tp_sl(aggregated_signal['signal'], current_price, indicators)

            return SignalResponse(
                symbol=symbol,
                signal=aggregated_signal['signal'],
                confidence=aggregated_signal['confidence'],
                reason=aggregated_signal['reason'],
                take_profit=tp_sl[0],
                stop_loss=tp_sl[1],
                entry_price=aggregated_signal.get('entry_price'),
                indicators=indicators,
                timestamp=datetime.utcnow().isoformat()
            )
        else:
            # Original single timeframe analysis
            kline_data = BybitService.fetch_klines(symbol, interval="240", limit=200)
            if kline_data.get("retCode") != 0:
                raise HTTPException(status_code=400, detail=kline_data.get("retMsg", "Failed to fetch klines"))

            klines = kline_data["result"]["list"]
            ta = TechnicalAnalysis(klines)
            indicators = ta.calculate_indicators()
            current_price = ta.get_latest_price()

            ai_generator = AISignalGenerator()
            signal_data = ai_generator.generate_signal(indicators, current_price, symbol)

            return SignalResponse(
                symbol=symbol,
                signal=signal_data['signal'],
                confidence=signal_data['confidence'],
                reason=signal_data['reason'],
                take_profit=signal_data['take_profit'],
                stop_loss=signal_data['stop_loss'],
                entry_price=signal_data.get('entry_price'),
                indicators=indicators,
                timestamp=datetime.utcnow().isoformat()
            )
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error generating signal: {str(e)}")

@app.get("/api/signals")
async def get_multiple_signals(symbols: Optional[str] = None) -> List[SignalResponse]:
    """Get signals for multiple symbols"""
    if not symbols:
        # Default top symbols
        symbols = "BTCUSDT,ETHUSDT,SOLUSDT,ADAUSDT,DOTUSDT"

    symbol_list = symbols.split(",")
    signals = []

    for symbol in symbol_list:
        try:
            signal = await get_signal(symbol.strip())
            signals.append(signal)
        except Exception as e:
            # Skip failed symbols
            continue

    return signals

@app.post("/api/ml/train/{symbol}")
async def train_ml_model(symbol: str, model_type: str = "rf"):
    """Train ML model for symbol"""
    try:
        # Fetch historical data for training (last 1000 candles)
        kline_data = BybitService.fetch_klines(symbol, interval="240", limit=1000)
        if kline_data.get("retCode") != 0:
            raise HTTPException(status_code=400, detail="Failed to fetch historical data")

        klines = kline_data["result"]["list"]

        # Prepare training data
        training_data = []
        for i, kline in enumerate(klines):
            ta = TechnicalAnalysis([kline])
            indicators = ta.calculate_indicators()
            price_changes = []
            volume_change = 0

            # Calculate price changes (simplified)
            close_prices = [float(k[4]) for k in klines[max(0, i-10):i+1]]
            if len(close_prices) > 1:
                price_changes = [(close_prices[j] - close_prices[j-1]) / close_prices[j-1] * 100
                               for j in range(1, min(11, len(close_prices)))]

            training_data.append({
                'indicators': indicators,
                'close': float(kline[4]),
                'price_changes': price_changes,
                'volume_change': volume_change
            })

        # Train ML model
        ml_predictor = MLSignalPredictor(model_type)
        result = ml_predictor.train_model(training_data, symbol)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@app.post("/api/backtest/{symbol}")
async def run_backtest(symbol: str, days: int = 30):
    """Run backtest on historical data"""
    try:
        # Fetch historical data
        kline_data = BybitService.fetch_klines(symbol, interval="240", limit=days*6)  # 6 candles per day
        if kline_data.get("retCode") != 0:
            raise HTTPException(status_code=400, detail="Failed to fetch historical data")

        klines = kline_data["result"]["list"]

        # Generate signals for each period
        signals_data = []
        price_data = []

        for kline in klines:
            ta = TechnicalAnalysis([kline])
            indicators = ta.calculate_indicators()
            current_price = ta.get_latest_price()

            ai_gen = AISignalGenerator()
            signal = ai_gen.generate_signal(indicators, current_price, symbol)

            signals_data.append({
                'timestamp': kline[0],
                'signal': signal['signal'],
                'confidence': signal['confidence'],
                'reason': signal['reason']
            })

            price_data.append({
                'timestamp': kline[0],
                'close': current_price
            })

        # Run backtest
        backtester = Backtester()
        results = backtester.run_backtest(signals_data, price_data)

        # Save results
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backtester.save_results(results, f"{symbol}_{timestamp}")

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")

@app.get("/api/ml/predict/{symbol}")
async def get_ml_prediction(symbol: str, model_type: str = "rf"):
    """Get ML-based signal prediction"""
    try:
        # Get current indicators
        kline_data = BybitService.fetch_klines(symbol, interval="240", limit=50)
        if kline_data.get("retCode") != 0:
            raise HTTPException(status_code=400, detail="Failed to fetch data")

        klines = kline_data["result"]["list"]
        ta = TechnicalAnalysis(klines)
        indicators = ta.calculate_indicators()

        # Calculate price changes
        price_changes = []
        volumes = [float(k[5]) for k in klines]
        if len(volumes) > 1:
            volume_change = (volumes[-1] - volumes[-2]) / volumes[-2] * 100
        else:
            volume_change = 0

        close_prices = [float(k[4]) for k in klines[-11:]]
        if len(close_prices) > 1:
            price_changes = [(close_prices[i] - close_prices[i-1]) / close_prices[i-1] * 100
                           for i in range(1, len(close_prices))]

        # Get ML prediction
        ml_predictor = MLSignalPredictor(model_type)
        prediction = ml_predictor.predict_signal(indicators, price_changes, volume_change, symbol)

        return prediction

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML prediction failed: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Bybit AI Swing Trader Backend API - Enhanced with ML & Backtesting"}