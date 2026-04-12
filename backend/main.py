import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from services.bybit_service import BybitService
from services.ta_analysis import TechnicalAnalysis
from services.ai_model import AISignalGenerator
from services.multi_timeframe import MultiTimeframeAnalysis
from services.ml_model import MLSignalPredictor
from services.backtester import Backtester
from services.demo_trading import demo_service
from services.advanced_ml import advanced_ml_service
from services.analytics import analytics_service
from infrastructure.database_service import DatabaseService
from core.logging.config import get_logger
from core.exceptions.handlers import global_exception_handler, log_request_middleware, BybitTraderException
from core.security.middleware import rate_limiting_middleware, input_validation_middleware, security_headers_middleware
from core.config.settings import get_settings
from core.websocket.manager import websocket_manager

# Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator

settings = get_settings()
from models.signal_model import SignalResponse, DemoSettingsRequest
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Initialize logging
logger = get_logger("main")

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Bybit AI Swing Trader...")
    try:
        # Initialize database on startup
        from core.database.config import db
        await db.create_tables()
        logger.info("Database initialized successfully")

        # Start WebSocket signal streaming
        logger.info("Starting WebSocket signal streaming...")
        streaming_task = asyncio.create_task(websocket_manager.start_signal_streaming())
        logger.info("WebSocket signal streaming started")

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Bybit AI Swing Trader...")
    try:
        # Stop WebSocket streaming
        await websocket_manager.stop_signal_streaming()
        logger.info("WebSocket streaming stopped")

        # Cancel streaming task if still running
        if 'streaming_task' in locals() and not streaming_task.done():
            streaming_task.cancel()
            try:
                await streaming_task
            except asyncio.CancelledError:
                pass
        logger.info("All background tasks stopped")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

from fastapi.middleware.cors import CORSMiddleware
from services.bybit_service import BybitService
from services.ta_analysis import TechnicalAnalysis
from services.ai_model import AISignalGenerator
from services.multi_timeframe import MultiTimeframeAnalysis
from services.ml_model import MLSignalPredictor
from services.backtester import Backtester
from services.demo_trading import demo_service
from infrastructure.database_service import DatabaseService
from models.signal_model import SignalResponse, DemoSettingsRequest
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

app = FastAPI(
    title="Bybit AI Swing Trader Backend",
    version="3.0.0",
    description="Enterprise-grade AI-powered swing trading system with real-time capabilities",
    lifespan=lifespan
)

# Initialize Prometheus metrics
Instrumentator().instrument(app).expose(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handler
app.add_exception_handler(Exception, global_exception_handler)

# Add request logging middleware
@app.middleware("http")
async def add_request_logging(request: Request, call_next):
    return await log_request_middleware(request, call_next)

# Add security middlewares
@app.middleware("http")
async def add_rate_limiting(request: Request, call_next):
    return await rate_limiting_middleware(request, call_next)

@app.middleware("http")
async def add_input_validation(request: Request, call_next):
    return await input_validation_middleware(request, call_next)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    return await security_headers_middleware(request, call_next)

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
        data = await BybitService.fetch_klines(symbol, interval, limit)
        if data.get("retCode") != 0:
            raise HTTPException(status_code=400, detail=data.get("retMsg", "Failed to fetch klines"))
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bybit API error: {str(e)}")

@app.get("/api/bybit/tickers")
async def get_tickers() -> dict:
    try:
        data = await BybitService.fetch_tickers()
        if data.get("retCode") != 0:
            raise HTTPException(status_code=400, detail=data.get("retMsg", "Failed to fetch tickers"))
        return data
    except Exception as e:
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
                kline_data = await BybitService.fetch_klines(symbol, interval="240", limit=200)
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
                
            # Save signal to database
            signal_data = {
                "symbol": symbol,
                "signal": final_signal,
                "confidence": ai_confidence,
                "timestamp": result["timestamp"] or datetime.utcnow(),
                "entry_price": result["latest_price"],
                "stop_loss": sl,
                "take_profit": tp,
                "reason": reason,
                "indicators": result["features"],
                "source": "live"
            }
            try:
                await DatabaseService.save_signal(signal_data)
            except Exception as e:
                logger.warning(f"Failed to save signal to database: {e}")

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

@app.get("/api/portfolio/correlation")
async def get_correlation_matrix(symbols: str = "BTCUSDT,ETHUSDT,SOLUSDT") -> Dict[str, Any]:
    """Calculate correlation matrix for multiple symbols"""
    try:
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]

        # Fetch price data for each symbol
        price_data = {}
        for symbol in symbol_list:
            kline_data = await BybitService.fetch_klines(symbol, interval="1d", limit=100)
            if kline_data.get("retCode") == 0:
                closes = [float(k[4]) for k in kline_data["result"]["list"]]
                price_data[symbol] = closes

        # Calculate correlation matrix
        import pandas as pd
        df = pd.DataFrame(price_data)
        correlation_matrix = df.corr().round(4).to_dict()

        return {
            "symbols": symbol_list,
            "correlation_matrix": correlation_matrix,
            "period_days": 100
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Correlation calculation failed: {str(e)}")

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

        # Chạy tác vụ huấn luyện nặng
        result_dict = await trainer.retrain_universal_model()
        
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
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Universal Training error: {str(e)}")

@app.post("/api/ml/train/{symbol}")
async def train_ml_model(symbol: str, model_type: str = "rf"):
    """Train ML model for symbol"""
    try:
        # Fetch historical data for training (last 1000 candles)
        kline_data = await BybitService.fetch_klines(symbol, interval="240", limit=1000)
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
async def run_backtest(symbol: str, days: int = 30, leverage: float = 10.0, min_hold_candles: int = 6, stop_loss_pct: float = 0.05, async_task: bool = False):
    """Run backtest on historical data. Use async_task=True for background processing."""
    try:
        if async_task:
            from tasks import run_backtest as backtest_task
            task = backtest_task.delay(symbol, days, leverage, min_hold_candles, stop_loss_pct)
            return {"task_id": task.id, "status": "running", "message": "Backtest started in background"}

        import asyncio
        # Chạy logic backtest nặng trong ThreadPool để không block server
        result = await asyncio.to_thread(_run_backtest_sync, symbol, days, leverage, min_hold_candles, stop_loss_pct)
        return result
    except Exception as e:
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")

@app.get("/api/backtest/status/{task_id}")
async def get_backtest_status(task_id: str):
    """Get status of async backtest task."""
    from celery.result import AsyncResult
    from celery_app import celery_app

    result = AsyncResult(task_id, app=celery_app)
    if result.state == "PENDING":
        response = {"state": result.state, "status": "Pending..."}
    elif result.state == "PROGRESS":
        response = {"state": result.state, "status": result.info}
    elif result.state == "SUCCESS":
        response = {"state": result.state, "result": result.result}
    else:
        response = {"state": result.state, "status": str(result.info)}

    return response

def _run_backtest_sync(symbol: str, days: int, leverage: float = 10.0, min_hold_candles: int = 6, stop_loss_pct: float = 0.05):
    # Fetch historical data (tăng limit lên để lấy đủ lịch sử tính toán)
    kline_data = asyncio.run(BybitService.fetch_klines(symbol, interval="240", limit=min(days*6 + 100, 1000)))  # 6 candles per day + 100 for indicators buffer
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

    # Save results to database
    try:
        # Add metadata to results
        results['symbol'] = symbol
        results['strategy_name'] = 'AI Swing Trader'
        from datetime import timedelta
        results['start_date'] = (datetime.utcnow() - timedelta(days=days)).isoformat()
        results['end_date'] = datetime.utcnow().isoformat()
        results['config'] = {
            'leverage': leverage,
            'min_hold_candles': min_hold_candles,
            'stop_loss_pct': stop_loss_pct
        }

        # Save synchronously since this function runs in a thread
        backtest_id = DatabaseService.save_backtest_result_sync(results, symbol)
        logger.info(f"Backtest saved to database with ID: {backtest_id}")
    except Exception as e:
        logger.error(f"Failed to save backtest to database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save backtest: {str(e)}")

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
        logger.error(traceback.format_exc())
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

# Database API Endpoints
@app.get("/api/backtests")
async def get_backtests(symbol: Optional[str] = None, limit: int = 20):
    """Get backtest results from database"""
    try:
        results = await DatabaseService.get_backtest_results(symbol, limit)
        return {"backtests": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Failed to get backtests: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get backtests: {str(e)}")

@app.get("/api/backtests/{backtest_id}")
async def get_backtest_detail(backtest_id: int):
    """Get detailed backtest result with trades"""
    try:
        result = await DatabaseService.get_backtest_by_id(backtest_id)
        if not result:
            raise HTTPException(status_code=404, detail="Backtest not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get backtest detail: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get backtest detail: {str(e)}")

@app.get("/api/signals/history")
async def get_signals_history(symbol: Optional[str] = None, limit: int = 50, hours: int = 24):
    """Get historical signals from database"""
    try:
        signals = await DatabaseService.get_signals(symbol, limit, hours)
        return {"signals": signals, "count": len(signals)}
    except Exception as e:
        logger.error(f"Failed to get signals history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get signals history: {str(e)}")

@app.get("/api/ml/models")
async def get_ml_models(active_only: bool = False):
    """Get ML models from database"""
    try:
        models = await DatabaseService.get_ml_models(active_only)
        return {"models": models, "count": len(models)}
    except Exception as e:
        logger.error(f"Failed to get ML models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ML models: {str(e)}")

@app.get("/api/stats")
async def get_statistics():
    """Get database statistics"""
    try:
        stats = await DatabaseService.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@app.websocket("/ws/signals/{symbol}")
async def websocket_signals(websocket: WebSocket, symbol: str):
    """WebSocket endpoint for real-time trading signals"""
    try:
        # Validate symbol
        if not symbol or not symbol.isalnum() or len(symbol) > 20:
            await websocket.close(code=1008, reason="Invalid symbol")
            return

        # Connect client
        await websocket_manager.connect(websocket, symbol.upper())

        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (optional)
                data = await websocket.receive_json()

                # Handle client commands
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
                elif data.get("type") == "stats":
                    stats = websocket_manager.get_connection_stats()
                    await websocket.send_json({"type": "stats", "data": stats})
                elif data.get("type") == "unsubscribe":
                    break

            except Exception as e:
                logger.warning(f"WebSocket message handling error: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {symbol}")
    except Exception as e:
        logger.error(f"WebSocket error for {symbol}: {e}")
    finally:
        websocket_manager.disconnect(websocket, symbol.upper())

@app.get("/api/websocket/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    try:
        stats = websocket_manager.get_connection_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get WebSocket stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get WebSocket stats: {str(e)}")

@app.post("/api/websocket/start-streaming")
async def start_websocket_streaming():
    """Start real-time signal streaming"""
    try:
        if websocket_manager.is_streaming:
            return {"status": "already_running", "message": "Signal streaming is already active"}

        # Start streaming in background task
        asyncio.create_task(websocket_manager.start_signal_streaming())

        return {"status": "started", "message": "Real-time signal streaming started"}
    except Exception as e:
        logger.error(f"Failed to start WebSocket streaming: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start streaming: {str(e)}")

@app.post("/api/websocket/stop-streaming")
async def stop_websocket_streaming():
    """Stop real-time signal streaming"""
    try:
        await websocket_manager.stop_signal_streaming()
        return {"status": "stopped", "message": "Real-time signal streaming stopped"}
    except Exception as e:
        logger.error(f"Failed to stop WebSocket streaming: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop streaming: {str(e)}")

# Advanced ML Endpoints
@app.post("/api/ml/train-advanced-universal")
async def train_advanced_universal_model(
    symbols: str,
    model_type: str = "ensemble",
    hyperparameter_tuning: bool = True,
    feature_selection: bool = True,
    cv_folds: int = 5
):
    """Train advanced universal ML model with hyperparameter tuning"""
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(',') if s.strip()]

        if len(symbol_list) == 0:
            raise HTTPException(status_code=400, detail="At least one symbol must be provided")

        if len(symbol_list) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 symbols allowed")

        # Validate model type
        allowed_types = ['rf', 'gb', 'ensemble']
        if model_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Model type must be one of: {allowed_types}"
            )

        result = await advanced_ml_service.train_advanced_universal_model(
            symbols=symbol_list,
            model_type=model_type or "ensemble",
            hyperparameter_tuning=hyperparameter_tuning if hyperparameter_tuning is not None else True,
            feature_selection=feature_selection if feature_selection is not None else True,
            cv_folds=cv_folds or 5
        )

        if result["status"] == "success":
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Training failed"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to train advanced universal model: {e}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@app.post("/api/ml/predict-advanced")
async def predict_with_advanced_model(
    symbol: str,
    features: Dict[str, float],
    model_name: Optional[str] = None
):
    """Make prediction using advanced ML model"""
    try:
        if not symbol or not symbol.isalnum() or len(symbol) > 20:
            raise HTTPException(status_code=400, detail="Invalid symbol")

        result = await advanced_ml_service.predict_signal(
            features=features,
            model_name=model_name
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to make advanced prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.get("/api/ml/advanced-models")
async def get_advanced_models():
    """Get all advanced ML models"""
    try:
        # Filter for advanced models
        all_models = await DatabaseService.get_ml_models()
        advanced_models = [
            model for model in all_models
            if model["model_type"].startswith("advanced_")
        ]

        return {"models": advanced_models, "count": len(advanced_models)}

    except Exception as e:
        logger.error(f"Failed to get advanced models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")

# Analytics Endpoints
@app.get("/api/analytics/portfolio")
async def get_portfolio_analytics(symbol: Optional[str] = None, days: int = 30):
    """Get comprehensive portfolio analytics"""
    try:
        analytics = await analytics_service.generate_portfolio_analytics(symbol, days)
        return analytics
    except Exception as e:
        logger.error(f"Failed to generate portfolio analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate analytics: {str(e)}")

@app.get("/api/analytics/performance")
async def get_performance_metrics(symbol: Optional[str] = None, days: int = 30):
    """Get key performance metrics"""
    try:
        full_analytics = await analytics_service.generate_portfolio_analytics(symbol, days)

        # Extract key metrics
        return {
            "summary": full_analytics.get("summary", {}),
            "basic_metrics": full_analytics.get("basic_metrics", {}),
            "performance_metrics": full_analytics.get("performance_metrics", {}),
            "risk_metrics": full_analytics.get("risk_metrics", {}),
            "recommendations": full_analytics.get("recommendations", [])
        }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Bybit AI Swing Trader Backend API - Enhanced with ML & Database"}