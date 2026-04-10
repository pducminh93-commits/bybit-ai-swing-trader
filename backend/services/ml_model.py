import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score, precision_recall_curve, auc
from typing import Dict, List, Any, Optional, Tuple
import joblib
import os
from datetime import datetime, timedelta
from services.model_manager import ModelManager

class MLSignalPredictor:
    def __init__(self, model_type: str = 'rf'):
        """
        Initialize ML predictor
        model_type: 'rf' (Random Forest), 'gb' (Gradient Boosting), 'ensemble'
        """
        self.model_type = model_type
        self.models = {}
        self.scalers = {}
        self.model_manager = ModelManager()
        self.feature_columns = [
            'rsi', 'macd', 'macd_signal', 'macd_hist',
            'bb_upper', 'bb_middle', 'bb_lower', 'stoch_k', 'stoch_d',
            'atr', 'adx', 'williams_r', 'cci', 'mfi',
            'tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b',
            'price_change_1', 'price_change_5', 'price_change_10',
            'volume_change', 'sma_20', 'sma_50', 'ema_12', 'ema_26'
        ]

    def prepare_features(self, indicators: Dict[str, Any], price_changes: List[float], volume_change: float) -> np.ndarray:
        """Prepare feature vector from indicators"""
        features = []

        for col in self.feature_columns:
            if col.startswith('price_change_'):
                idx = int(col.split('_')[-1])
                if idx < len(price_changes):
                    features.append(price_changes[idx])
                else:
                    features.append(0.0)
            elif col == 'volume_change':
                features.append(volume_change)
            else:
                val = indicators.get(col, 0)
                # Thay thế None hoặc giá trị không phải số thành 0.0
                if val is None or pd.isna(val):
                    val = 0.0
                features.append(val)

        # Chuyển đổi thành Numpy Array và thay thế hoàn toàn mọi giá trị NaN, Inf còn sót lại thành 0
        arr = np.array(features).reshape(1, -1)
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        return arr

    def train_model(self, historical_data: List[Dict[str, Any]], symbol: str) -> Dict[str, Any]:
        """Train ML model on historical data"""
        if len(historical_data) < 100:  # Need minimum data
            return {'status': 'insufficient_data'}

        # Prepare dataset
        X = []
        y = []

        for i in range(20, len(historical_data) - 5):  # Look ahead 5 periods
            current_indicators = historical_data[i]['indicators']
            price_changes = historical_data[i]['price_changes']
            volume_change = historical_data[i]['volume_change']

            # Create feature vector
            features = self.prepare_features(current_indicators, price_changes, volume_change)
            X.append(features.flatten())

            # Determine future price movement (target)
            future_prices = [d['close'] for d in historical_data[i+1:i+6]]
            current_price = historical_data[i]['close']

            if future_prices:
                max_future = max(future_prices)
                min_future = min(future_prices)

                # Define target based on future movement
                upside = (max_future - current_price) / current_price * 100
                downside = (current_price - min_future) / current_price * 100

                if upside > 2 and upside > downside:  # Strong upward movement
                    target = 2  # BUY
                elif downside > 2 and downside > upside:  # Strong downward movement
                    target = 0  # SELL
                else:
                    target = 1  # HOLD
            else:
                target = 1  # HOLD

            y.append(target)

        if len(X) < 50:
            return {'status': 'insufficient_data'}

        X = np.array(X)
        y = np.array(y)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train model
        if self.model_type == 'rf':
            model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
        elif self.model_type == 'gb':
            model = GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=5)
        else:  # ensemble
            rf_model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
            gb_model = GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=5)
            # Mix (Soft Voting): Lấy trung bình xác suất của cả 2 thuật toán để quyết định
            model = VotingClassifier(
                estimators=[('rf', rf_model), ('gb', gb_model)],
                voting='soft'
            )

        model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)

        # Store model and scaler
        self.models[symbol] = model
        self.scalers[symbol] = scaler

        # Save model
        self._save_model(symbol, model, scaler)
        
        # Get feature importances safely
        feature_importance = None
        if hasattr(model, 'feature_importances_'):
            feature_importance = dict(zip(self.feature_columns, model.feature_importances_))
        elif isinstance(model, VotingClassifier):
            # For VotingClassifier, we can average the importances of underlying models if they have them
            try:
                rf_imp = model.named_estimators_['rf'].feature_importances_
                gb_imp = model.named_estimators_['gb'].feature_importances_
                avg_imp = (rf_imp + gb_imp) / 2
                feature_importance = dict(zip(self.feature_columns, avg_imp))
            except:
                pass

        return {
            'status': 'trained',
            'accuracy': float(accuracy),
            'feature_importance': feature_importance,
            'classification_report': classification_report(y_test, y_pred, output_dict=True),
            'evaluation': self.evaluate_model(X_test, y_test)
        }

    def evaluate_model(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """Evaluate model with comprehensive metrics"""
        if not hasattr(self, 'model') or self.model is None:
            return {'error': 'No model trained'}

        try:
            # Need to train model first to have it
            # This is a placeholder - in practice, evaluate after training
            y_pred = self.model.predict(X_test)
            y_pred_proba = self.model.predict_proba(X_test)[:, 1] if hasattr(self.model, 'predict_proba') else None

            metrics = {
                'accuracy': accuracy_score(y_test, y_pred),
                'classification_report': classification_report(y_test, y_pred, output_dict=True),
            }

            if y_pred_proba is not None:
                metrics['auc'] = roc_auc_score(y_test, y_pred_proba)

                # Precision-Recall curve
                precision, recall, _ = precision_recall_curve(y_test, y_pred_proba)
                metrics['pr_auc'] = auc(recall, precision)

            return metrics

        except Exception as e:
            return {'error': str(e)}

    def predict_signal(self, indicators: Dict[str, Any], price_changes: List[float],
                       volume_change: float, symbol: str) -> Dict[str, Any]:
        """Predict signal using trained ML model"""
        if symbol not in self.models:
            # Try to load saved model
            if not self._load_model(symbol):
                return {'signal': 'HOLD', 'confidence': 0.0, 'reason': 'No trained model available'}

        model = self.models[symbol]
        scaler = self.scalers[symbol]

        # Prepare features
        features = self.prepare_features(indicators, price_changes, volume_change)
        features_scaled = scaler.transform(features)

        # Predict
        prediction = model.predict(features_scaled)[0]
        probabilities = model.predict_proba(features_scaled)[0]

        # Map prediction to signal (SỬA THÀNH LONG/SHORT CHO KHỚP VỚI BACKTESTER VÀ HỆ THỐNG CŨ)
        signal_map = {0: 'SHORT', 1: 'HOLD', 2: 'LONG'}
        signal = signal_map.get(prediction, 'HOLD')
        confidence = max(probabilities)

        return {
            'signal': signal,
            'confidence': float(confidence),
            'probabilities': {
                'SHORT': float(probabilities[0]),
                'HOLD': float(probabilities[1]),
                'LONG': float(probabilities[2])
            },
            'reason': f'ML prediction: {signal} ({confidence:.2f} confidence)'
        }

    def _save_model(self, symbol: str, model, scaler):
        """Save trained model and scaler"""
        os.makedirs('models', exist_ok=True)
        joblib.dump(model, f'models/{symbol}_{self.model_type}_model.pkl')
        joblib.dump(scaler, f'models/{symbol}_{self.model_type}_scaler.pkl')

    def _load_model(self, symbol: str) -> bool:
        """Load saved model and scaler (Universal first, then Auto-select Best Specific)"""
        # 1. Ưu tiên load Universal Ensemble Model trước (Trí tuệ toàn cầu)
        universal_model_path = 'models/universal_ensemble_model.pkl'
        universal_scaler_path = 'models/universal_ensemble_scaler.pkl'
        
        if os.path.exists(universal_model_path) and os.path.exists(universal_scaler_path):
            try:
                # Use ModelManager for model
                self.models[symbol] = self.model_manager.get_model('universal_ensemble')
                if self.models[symbol] is None:
                    # Load manually if not cached
                    self.models[symbol] = joblib.load(universal_model_path)
                    self.model_manager.save_model('universal_ensemble', self.models[symbol])
                self.scalers[symbol] = joblib.load(universal_scaler_path)
                
                # NẾU LÀ UNIVERSAL MODEL, cập nhật lại danh sách features thành 20 features của FeatureEngineer
                self.feature_columns = [
                    'openInterest', 'fundingRate', 'rsi_14', 'macd', 'macd_signal', 'macd_hist', 
                    'atr_14', 'adx_14', 'bb_upper', 'bb_middle', 'bb_lower', 'volatility_atr_ratio', 
                    'obv', 'cmf', 'oi_change_1', 'oi_change_4', 'price_change_1', 'sentiment_score', 
                    'funding_rate_ma3', 'is_extreme_funding'
                ]
                return True
            except Exception as e:
                pass # Fallback if universal fails
                
        # 2. Khám phá các Model cục bộ (Theo symbol)
        # Thứ tự ưu tiên độ thông minh: ensemble > gb > rf
        priorities = [self.model_type, 'ensemble', 'gb', 'rf']
        # Loại bỏ trùng lặp giữ nguyên thứ tự
        check_order = []
        for p in priorities:
            if p not in check_order:
                check_order.append(p)

        for m_type in check_order:
            model_path = f'models/{symbol}_{m_type}_model.pkl'
            scaler_path = f'models/{symbol}_{m_type}_scaler.pkl'

            if os.path.exists(model_path) and os.path.exists(scaler_path):
                try:
                    # Use ModelManager for model
                    model_key = f"{symbol}_{m_type}"
                    self.models[symbol] = self.model_manager.get_model(model_key)
                    if self.models[symbol] is None:
                        self.models[symbol] = joblib.load(model_path)
                        self.model_manager.save_model(model_key, self.models[symbol])
                    self.scalers[symbol] = joblib.load(scaler_path)
                    self.model_type = m_type # Cập nhật lại type đang dùng
                    
                    # NẾU LÀ LOCAL MODEL (cũ), danh sách features là 26 features cơ bản
                    self.feature_columns = [
                        'rsi', 'macd', 'macd_signal', 'macd_hist',
                        'bb_upper', 'bb_middle', 'bb_lower', 'stoch_k', 'stoch_d',
                        'atr', 'adx', 'williams_r', 'cci', 'mfi',
                        'tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b',
                        'price_change_1', 'price_change_5', 'price_change_10',
                        'volume_change', 'sma_20', 'sma_50', 'ema_12', 'ema_26'
                    ]
                    return True
                except:
                    continue # Thử model tiếp theo nếu file bị lỗi
                    
        return False

    def get_feature_importance(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get feature importance for trained model"""
        if symbol in self.models:
            model = self.models[symbol]
            if hasattr(model, 'feature_importances_'):
                return dict(zip(self.feature_columns, model.feature_importances_))
            elif isinstance(model, VotingClassifier):
                try:
                    rf_imp = model.named_estimators_['rf'].feature_importances_
                    gb_imp = model.named_estimators_['gb'].feature_importances_
                    avg_imp = (rf_imp + gb_imp) / 2
                    return dict(zip(self.feature_columns, avg_imp))
                except:
                    pass
        return None