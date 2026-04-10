import requests
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services.bybit_service import BybitService
from services.ta_analysis import TechnicalAnalysis
from services.ai_model import AISignalGenerator
from services.multi_timeframe import MultiTimeframeAnalysis
from services.ml_model import MLSignalPredictor
from services.backtester import Backtester
from services.demo_trading import demo_service
from models.signal_model import SignalResponse, DemoSettingsRequest
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
            # SỬ DỤNG HỆ THỐNG AI MỚI NHẤT: Universal Ensemble + Risk Manager
            from services.signal_integrator import AdvancedSignalIntegrator
            
            integrator = AdvancedSignalIntegrator(symbol)
            result = integrator.generate_actionable_signal()
            
            if "status" in result and result["status"] == "error":
                raise HTTPException(status_code=400, detail=result.get("message"))
                
            trade_decision = result["trade_decision"]
            raw_signal = result["raw_signal"]
            ai_confidence = result["ai_confidence"]
            
            # Nếu Risk Manager quyết định SKIP, ta trả về tín hiệu HOLD (bỏ qua lệnh)
            if trade_decision["action"] == "SKIP":
                final_signal = "HOLD"
                reason = trade_decision.get("reason", "Skipped by Risk Manager")
                tp = 0.0
                sl = 0.0
            else:
                final_signal = trade_decision["signal"]
                reason = trade_decision.get("notes", f"Execute {final_signal}")
                tp = trade_decision["take_profit"]
                sl = trade_decision["stop_loss"]
                
            return SignalResponse(
                symbol=symbol,
                signal=final_signal,
                confidence=ai_confidence,
                reason=reason,
                take_profit=tp,
                stop_loss=sl,
                entry_price=result["latest_price"],
                indicators=result["features"],
                timestamp=result["timestamp"] or datetime.utcnow().isoformat()
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

@app.post("/api/ml/train-universal")
async def train_universal_model(symbols: str = "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,DOGEUSDT"):
    """Train Universal/Global ML model for multiple symbols (Siêu tập dữ liệu)"""
    try:
        import asyncio
        from services.retrainer import WalkForwardTrainer
        
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            raise HTTPException(status_code=400, detail="Symbols list cannot be empty")
            
        trainer = WalkForwardTrainer(symbols=symbol_list)
        
        # Chạy tác vụ huấn luyện nặng trong ThreadPool để không làm treo Web Server
        result_dict = await asyncio.to_thread(trainer.retrain_universal_model)
        
        if result_dict and isinstance(result_dict, dict) and result_dict.get("status") == "success":
            return {
                "status": "success", 
                "message": f"Universal Ensemble Model trained successfully on {len(symbol_list)} symbols",
                "symbols_used": symbol_list,
                "accuracy": result_dict.get("accuracy", 0),
                "feature_importance": result_dict.get("feature_importance", {})
            }
        else:
            raise HTTPException(status_code=500, detail="Universal training failed. Check logs for details.")
            
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Universal Training error: {str(e)}")

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
async def run_backtest(symbol: str, days: int = 30, leverage: float = 10.0, min_hold_candles: int = 6, stop_loss_pct: float = 0.05):
    """Run backtest on historical data"""
    try:
        import asyncio
        # Chạy logic backtest nặng trong ThreadPool để không block server
        result = await asyncio.to_thread(_run_backtest_sync, symbol, days, leverage, min_hold_candles)
        return result
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")

def _run_backtest_sync(symbol: str, days: int, leverage: float = 10.0, min_hold_candles: int = 6, stop_loss_pct: float = 0.05):
    # Fetch historical data (tăng limit lên để lấy đủ lịch sử tính toán)
    kline_data = BybitService.fetch_klines(symbol, interval="240", limit=min(days*6 + 100, 1000))  # 6 candles per day + 100 for indicators buffer
    if kline_data.get("retCode") != 0:
        raise ValueError("Failed to fetch historical data")

    klines = kline_data["result"]["list"][::-1] # Đảo ngược từ quá khứ -> hiện tại
    
    # CỐ GẮNG KÉO THÊM DỮ LIỆU OI & FUNDING (MAX 200 CỦA BYBIT) CHO BACKTEST UNIVERSAL MODEL
    try:
        oi_data = BybitService.fetch_open_interest(symbol, intervalTime="4h", limit=500).get('result', {}).get('list', [])
        fr_data = BybitService.fetch_funding_rate_history(symbol, limit=500).get('result', {}).get('list', [])
    except:
        oi_data = []
        fr_data = []

    # Generate signals for each period
    signals_data = []
    price_data = []

    from services.ml_model import MLSignalPredictor
    from services.feature_engineering import FeatureEngineer
    
    predictor = MLSignalPredictor()
    has_model = predictor._load_model(symbol)

    start_idx = 50
    if len(klines) <= start_idx:
        raise ValueError("Not enough historical data for backtesting")

    # TỐI ƯU HÓA: Tính toán FeatureEngineer 1 LẦN DUY NHẤT cho toàn bộ chuỗi thời gian
    is_universal = has_model and len(predictor.feature_columns) == 20
    master_df = None
    
    if is_universal:
        eng = FeatureEngineer(klines, oi_data, fr_data)
        master_df = eng.generate_all_features()
        # Chuyển index (datetime) thành chuỗi milliseconds (str) để tra cứu
        if not master_df.empty:
            import pandas as pd
            # Chuyển đổi an toàn từ DatetimeIndex -> int64 (nanoseconds) -> int (milliseconds) -> str
            # pd.to_numeric() chuyển DatetimeIndex về int64 (ns). Nên cần chia cho 10**6 (1 triệu) để về ms
            master_df.index = (pd.to_numeric(master_df.index) // 10**6).astype(str)

    for i in range(start_idx, len(klines)):
        current_kline = klines[i]
        timestamp = current_kline[0]
        current_price = float(current_kline[4])
        
        indicators = {}
        if is_universal and master_df is not None:
            # Look up features pre-calculated for this specific timestamp
            if timestamp in master_df.index:
                indicators = master_df.loc[timestamp].to_dict()
            else:
                # Fallback if timestamp missing due to DropNA
                history_window = klines[max(0, i-100):i+1] 
                ta = TechnicalAnalysis(history_window)
                indicators = ta.calculate_indicators()
        else:
            # NẾU LÀ LOCAL MODEL CŨ (Hoặc chưa có)
            history_window = klines[max(0, i-100):i+1] 
            ta = TechnicalAnalysis(history_window)
            indicators = ta.calculate_indicators()

        # Gọi não bộ ML (Nếu đã train) hoặc Logic cũ
        if has_model:
            price_changes_mock = [0.0]*10
            pred = predictor.predict_signal(indicators, price_changes_mock, 0.0, symbol)
            final_signal = pred.get('signal', 'HOLD')
            confidence = pred.get('confidence', 0.5)
            reason = pred.get('reason', 'ML Prediction')
        else:
            ai_gen = AISignalGenerator()
            signal_out = ai_gen.generate_signal(indicators, current_price, symbol)
            final_signal = signal_out['signal']
            confidence = signal_out['confidence']
            reason = signal_out['reason']

        signals_data.append({
            'timestamp': timestamp,
            'signal': final_signal,
            'confidence': confidence,
            'reason': reason
        })

        price_data.append({
            'timestamp': timestamp,
            'close': current_price
        })

    # Run backtest
    backtester = Backtester(initial_balance=100, leverage=leverage, min_hold_candles=min_hold_candles, stop_loss_pct=stop_loss_pct)
    results = backtester.run_backtest(signals_data, price_data)

    # Save results
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backtester.save_results(results, f"{symbol}_{timestamp_str}")

    return results

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

# Demo Trading Endpoints
@app.post("/api/demo/start")
async def start_demo_simulation():
    """Start the demo trading simulation"""
    try:
        demo_service.start_simulation()
        return {"status": "started", "message": "Demo simulation started successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start simulation: {str(e)}")

@app.post("/api/demo/stop")
async def stop_demo_simulation():
    """Stop the demo trading simulation"""
    try:
        demo_service.stop_simulation()
        return {"status": "stopped", "message": "Demo simulation stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop simulation: {str(e)}")

@app.post("/api/demo/process-signals")
async def process_demo_signals(signals: List[SignalResponse]):
    """Process signals for demo trading"""
    try:
        executed_trades = demo_service.process_signals(signals)
        demo_service.update_positions()  # Update positions after processing signals
        return {"executed_trades": executed_trades or [], "count": len(executed_trades or [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process signals: {str(e)}")

@app.get("/api/demo/status")
async def get_demo_status():
    """Get demo trading status and balance"""
    try:
        return {
            "is_running": demo_service.is_running,
            "balance": demo_service.get_balance(),
            "capital": demo_service.capital,
            "leverage": demo_service.leverage,
            "position_size_pct": demo_service.position_size_pct,
            "total_positions": len(demo_service.get_open_positions()),
            "total_trades": len(demo_service.get_trade_history())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@app.get("/api/demo/positions")
async def get_demo_positions():
    """Get all open demo positions"""
    try:
        positions = demo_service.get_open_positions()
        return {"positions": positions, "count": len(positions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get positions: {str(e)}")

@app.get("/api/demo/history")
async def get_demo_history():
    """Get demo trading history"""
    try:
        history = demo_service.get_trade_history()
        return {"history": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

@app.post("/api/demo/settings")
async def update_demo_settings(
    settings: dict
):
    """Update demo trading settings"""
    try:
        # Safely extract and convert values
        capital = settings.get('capital')
        leverage = settings.get('leverage')
        position_size_pct = settings.get('position_size_pct')
        reset_data = settings.get('reset_data', False)

        demo_service.update_settings(
            capital=float(capital) if capital is not None else None,
            leverage=float(leverage) if leverage is not None else None,
            position_size_pct=float(position_size_pct) if position_size_pct is not None else None,
            reset_data=bool(reset_data)
        )
        return {
            "status": "updated",
            "settings": {
                "capital": float(demo_service.capital),
                "leverage": float(demo_service.leverage),
                "position_size_pct": float(demo_service.position_size_pct)
            }
        }
    except Exception as e:
        import traceback
        print(f"Error updating demo settings: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/demo/reset")
async def reset_demo_simulation():
    """Reset the demo trading simulation"""
    try:
        demo_service.stop_simulation()
        demo_service.positions.clear()
        demo_service.history.clear()
        demo_service.capital = 100.0
        demo_service.leverage = 1.0
        demo_service.position_size_pct = 10.0
        return {"status": "reset", "message": "Demo simulation reset successfully"}
    except Exception as e:
        print(f"Error resetting demo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Bybit AI Swing Trader Backend API - Enhanced with ML & Backtesting"}