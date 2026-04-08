import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
from typing import Dict, List, Any, Optional, Tuple
import joblib
import os
from datetime import datetime, timedelta

class MLSignalPredictor:
    def __init__(self, model_type: str = 'rf'):
        """
        Initialize ML predictor
        model_type: 'rf' (Random Forest), 'gb' (Gradient Boosting), 'ensemble'
        """
        self.model_type = model_type
        self.models = {}
        self.scalers = {}
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
                features.append(indicators.get(col, 0) or 0)

        return np.array(features).reshape(1, -1)

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
            rf_model = RandomForestClassifier(n_estimators=50, random_state=42)
            gb_model = GradientBoostingClassifier(n_estimators=50, random_state=42)
            # For simplicity, use RF as primary
            model = rf_model

        model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)

        # Store model and scaler
        self.models[symbol] = model
        self.scalers[symbol] = scaler

        # Save model
        self._save_model(symbol, model, scaler)

        return {
            'status': 'trained',
            'accuracy': accuracy,
            'feature_importance': dict(zip(self.feature_columns, model.feature_importances_)) if hasattr(model, 'feature_importances_') else None,
            'classification_report': classification_report(y_test, y_pred, output_dict=True)
        }

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

        # Map prediction to signal
        signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        signal = signal_map.get(prediction, 'HOLD')
        confidence = max(probabilities)

        return {
            'signal': signal,
            'confidence': float(confidence),
            'probabilities': {
                'SELL': float(probabilities[0]),
                'HOLD': float(probabilities[1]),
                'BUY': float(probabilities[2])
            },
            'reason': f'ML prediction: {signal} ({confidence:.2f} confidence)'
        }

    def _save_model(self, symbol: str, model, scaler):
        """Save trained model and scaler"""
        os.makedirs('models', exist_ok=True)
        joblib.dump(model, f'models/{symbol}_{self.model_type}_model.pkl')
        joblib.dump(scaler, f'models/{symbol}_{self.model_type}_scaler.pkl')

    def _load_model(self, symbol: str) -> bool:
        """Load saved model and scaler"""
        model_path = f'models/{symbol}_{self.model_type}_model.pkl'
        scaler_path = f'models/{symbol}_{self.model_type}_scaler.pkl'

        if os.path.exists(model_path) and os.path.exists(scaler_path):
            try:
                self.models[symbol] = joblib.load(model_path)
                self.scalers[symbol] = joblib.load(scaler_path)
                return True
            except:
                return False
        return False

    def get_feature_importance(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get feature importance for trained model"""
        if symbol in self.models and hasattr(self.models[symbol], 'feature_importances_'):
            return dict(zip(self.feature_columns, self.models[symbol].feature_importances_))
        return None