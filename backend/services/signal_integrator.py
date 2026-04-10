from typing import Dict, Any, Tuple
from services.bybit_service import BybitService
from services.feature_engineering import FeatureEngineer
from services.risk_manager import RiskManager
from services.ml_model import MLSignalPredictor

class AdvancedSignalIntegrator:
    def __init__(self, symbol: str, capital: float = 1000.0):
        self.symbol = symbol
        self.capital = capital
        self.predictor = MLSignalPredictor(model_type='rf')
        self.risk_manager = RiskManager()
        
    def generate_actionable_signal(self) -> Dict[str, Any]:
        """
        Kéo dữ liệu -> Tạo Đặc trưng -> Dự đoán ML -> Quản lý Rủi ro -> Trả về Lệnh cuối cùng
        """
        # 1. Fetch Data (MẮT)
        klines_resp = BybitService.fetch_klines(self.symbol, interval="240", limit=200)
        oi_resp = BybitService.fetch_open_interest(self.symbol, intervalTime="4h", limit=200)
        fr_resp = BybitService.fetch_funding_rate_history(self.symbol, limit=200)
        
        klines = klines_resp.get('result', {}).get('list', [])
        oi_data = oi_resp.get('result', {}).get('list', [])
        fr_data = fr_resp.get('result', {}).get('list', [])
        
        if not klines:
            return {"status": "error", "message": "Failed to fetch klines"}
            
        current_price = float(klines[0][4]) # Close price of latest kline
        
        # 2. Feature Engineering (NÃO BỘ)
        engineer = FeatureEngineer(klines, oi_data, fr_data)
        df = engineer.generate_all_features()
        if df.empty:
            return {"status": "error", "message": "Not enough data to generate features"}
            
        latest_features = df.iloc[-1].to_dict()
        
        # 3. AI Prediction (DỰ ĐOÁN)
        # _load_model sẽ ưu tiên nạp universal_ensemble_model.pkl (Bộ não Toàn cầu)
        is_trained = self.predictor._load_model(self.symbol)
        
        raw_signal = "HOLD"
        confidence = 0.5
        
        if is_trained:
            # Model Toàn Cầu đã sẵn sàng! Đưa features vào để lấy dự đoán
            # Vì ta bỏ qua price_changes/volume_change ở model universal, nhưng hàm cũ vẫn cần
            price_changes_mock = [0.0]*10 
            pred_result = self.predictor.predict_signal(
                indicators=latest_features, 
                price_changes=price_changes_mock, 
                volume_change=0.0, 
                symbol=self.symbol
            )
            raw_signal = pred_result.get('signal', 'HOLD')
            confidence = pred_result.get('confidence', 0.5)
        else:
            # Fallback (Chưa có Model Toàn cầu thì dùng logic rule-based cổ điển)
            rsi = latest_features.get('rsi_14', 50)
            macd = latest_features.get('macd', 0)
            macd_signal = latest_features.get('macd_signal', 0)
            
            if rsi < 30 and macd > macd_signal:
                raw_signal = "LONG"
                confidence = 0.75 + (30 - rsi)/100
            elif rsi > 70 and macd < macd_signal:
                raw_signal = "SHORT"
                confidence = 0.75 + (rsi - 70)/100
            else:
                confidence = 0.5
            
        # 4. Risk Management (KHIÊN)
        atr = latest_features.get('atr_14', current_price * 0.02)
        adx = latest_features.get('adx_14', 25)
        is_extreme_funding = bool(latest_features.get('is_extreme_funding', 0))
        
        trade_decision = self.risk_manager.evaluate_trade(
            capital=self.capital,
            current_price=current_price,
            signal=raw_signal,
            ai_confidence=confidence,
            atr=atr,
            adx=adx,
            is_extreme_funding=is_extreme_funding
        )
        
        return {
            "symbol": self.symbol,
            "timestamp": df.index[-1].isoformat() if not df.empty else None,
            "latest_price": current_price,
            "raw_signal": raw_signal,
            "ai_confidence": confidence,
            "features": {
                "rsi": round(rsi, 2),
                "atr": round(atr, 2),
                "adx": round(adx, 2),
                "is_extreme_funding": is_extreme_funding
            },
            "trade_decision": trade_decision
        }
