from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.feature_selection import SelectKBest, f_classif
import joblib
import os
from pathlib import Path

from core.logging.config import get_logger
from core.config.settings import settings
from infrastructure.database_service import DatabaseService

logger = get_logger("advanced_ml")

class AdvancedMLService:
    """Advanced ML service with hyperparameter tuning and ensemble methods"""

    def __init__(self):
        self.models_dir = Path("models")
        self.models_dir.mkdir(exist_ok=True)
        self.scalers_dir = Path("models/scalers")
        self.scalers_dir.mkdir(exist_ok=True)

    async def train_advanced_universal_model(
        self,
        symbols: List[str],
        model_type: Optional[str] = "ensemble",
        hyperparameter_tuning: Optional[bool] = True,
        feature_selection: Optional[bool] = True,
        cv_folds: Optional[int] = 5
    ) -> Dict[str, Any]:
        """
        Train advanced universal model with hyperparameter tuning

        Args:
            symbols: List of symbols to train on
            model_type: Type of model ('rf', 'gb', 'ensemble')
            hyperparameter_tuning: Whether to perform hyperparameter tuning
            feature_selection: Whether to perform feature selection
            cv_folds: Number of cross-validation folds

        Returns:
            Dict containing training results and metrics
        """
        try:
            logger.info(f"Starting advanced universal model training for symbols: {symbols}")

            # Collect data from all symbols
            all_features = []
            all_targets = []

            for symbol in symbols:
                try:
                    # Get recent signals from database
                    signals = await DatabaseService.get_signals(symbol, hours=720)  # 30 days

                    if len(signals) < 100:
                        logger.warning(f"Insufficient data for {symbol}: {len(signals)} signals")
                        continue

                    # Convert to features and targets
                    symbol_features, symbol_targets = await self._prepare_symbol_data(signals)
                    all_features.extend(symbol_features)
                    all_targets.extend(symbol_targets)

                    logger.info(f"Processed {len(symbol_features)} samples from {symbol}")

                except Exception as e:
                    logger.error(f"Failed to process data for {symbol}: {e}")
                    continue

            if len(all_features) < 1000:
                raise ValueError(f"Insufficient training data: {len(all_features)} samples")

            # Convert to numpy arrays
            X = np.array(all_features)
            y = np.array(all_targets)

            logger.info(f"Training on {len(X)} samples with {X.shape[1]} features")

            # Feature selection (optional)
            if feature_selection:
                X, selected_features = await self._perform_feature_selection(X, y)
                logger.info(f"Selected {len(selected_features)} features")

            # Split data
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            # Train model
            if model_type == "rf":
                model, scaler, metrics = await self._train_random_forest(
                    X_train, y_train, X_test, y_test, hyperparameter_tuning
                )
            elif model_type == "gb":
                model, scaler, metrics = await self._train_gradient_boosting(
                    X_train, y_train, X_test, y_test, hyperparameter_tuning
                )
            elif model_type == "ensemble":
                model, scaler, metrics = await self._train_ensemble(
                    X_train, y_train, X_test, y_test, hyperparameter_tuning
                )
            else:
                raise ValueError(f"Unsupported model type: {model_type}")

            # Save model
            model_name = f"advanced_universal_{model_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            model_path = self.models_dir / f"{model_name}.pkl"
            scaler_path = self.scalers_dir / f"{model_name}_scaler.pkl"

            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)

            # Save to database
            await DatabaseService.save_ml_model({
                "name": model_name,
                "model_type": f"advanced_{model_type}",
                "symbols": symbols,
                "accuracy": metrics["accuracy"],
                "feature_importance": metrics.get("feature_importance", {}),
                "model_path": str(model_path),
                "scaler_path": str(scaler_path),
                "training_samples": len(X_train),
                "validation_accuracy": metrics["accuracy"],
                "is_active": True,
                "version": "2.0.0"
            })

            logger.info(f"Advanced universal model trained successfully: {model_name}")

            return {
                "status": "success",
                "model_name": model_name,
                "model_type": model_type,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "metrics": metrics,
                "symbols_trained": symbols,
                "hyperparameter_tuning": hyperparameter_tuning,
                "feature_selection": feature_selection
            }

        except Exception as e:
            logger.error(f"Failed to train advanced universal model: {e}")
            return {
                "status": "error",
                "error": str(e),
                "symbols_attempted": symbols
            }

    async def _prepare_symbol_data(self, signals: List[Dict[str, Any]]) -> Tuple[List[List[float]], List[int]]:
        """Prepare signal data for ML training"""
        features = []
        targets = []

        for signal in signals:
            try:
                # Extract features from signal
                feature_vector = [
                    signal.get("rsi_14", 50.0),
                    signal.get("macd", 0.0),
                    signal.get("macd_signal", 0.0),
                    signal.get("macd_hist", 0.0),
                    signal.get("atr_14", 100.0),
                    signal.get("adx_14", 25.0),
                    signal.get("bb_upper", 0.0),
                    signal.get("bb_middle", 0.0),
                    signal.get("bb_lower", 0.0),
                    signal.get("open_interest", 0.0),
                    signal.get("funding_rate", 0.0),
                    signal.get("ai_confidence", 0.5)
                ]

                # Convert signal type to numeric target
                signal_type = signal.get("signal_type", "HOLD")
                if signal_type == "LONG":
                    target = 1
                elif signal_type == "SHORT":
                    target = 0
                else:  # HOLD
                    continue  # Skip hold signals for binary classification

                features.append(feature_vector)
                targets.append(target)

            except Exception as e:
                logger.warning(f"Failed to process signal: {e}")
                continue

        return features, targets

    async def _perform_feature_selection(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, List[int]]:
        """Perform feature selection"""
        try:
            selector = SelectKBest(score_func=f_classif, k=8)  # Select top 8 features
            X_selected = selector.fit_transform(X, y)

            selected_features = selector.get_support(indices=True).tolist()
            logger.info(f"Selected features: {selected_features}")

            return X_selected, selected_features

        except Exception as e:
            logger.warning(f"Feature selection failed: {e}")
            return X, list(range(X.shape[1]))

    async def _train_random_forest(
        self, X_train: np.ndarray, y_train: np.ndarray,
        X_test: np.ndarray, y_test: np.ndarray,
        hyperparameter_tuning: bool = True
    ) -> Tuple[Any, Any, Dict[str, Any]]:
        """Train Random Forest with hyperparameter tuning"""

        if hyperparameter_tuning:
            param_grid = {
                'n_estimators': [100, 200, 300],
                'max_depth': [10, 20, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4],
                'max_features': ['sqrt', 'log2']
            }

            rf = RandomForestClassifier(random_state=42, n_jobs=-1)
            grid_search = GridSearchCV(
                rf, param_grid, cv=3, scoring='accuracy', n_jobs=-1, verbose=1
            )
            grid_search.fit(X_train, y_train)

            best_model = grid_search.best_estimator_
            logger.info(f"Best RF params: {grid_search.best_params_}")
        else:
            best_model = RandomForestClassifier(
                n_estimators=200, max_depth=20, random_state=42, n_jobs=-1
            )
            best_model.fit(X_train, y_train)

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Retrain on scaled data
        best_model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = best_model.predict(X_test_scaled)
        metrics = self._calculate_metrics(y_test, y_pred)

        # Feature importance
        metrics["feature_importance"] = dict(enumerate(best_model.feature_importances_))

        return best_model, scaler, metrics

    async def _train_gradient_boosting(
        self, X_train: np.ndarray, y_train: np.ndarray,
        X_test: np.ndarray, y_test: np.ndarray,
        hyperparameter_tuning: bool = True
    ) -> Tuple[Any, Any, Dict[str, Any]]:
        """Train Gradient Boosting with hyperparameter tuning"""

        if hyperparameter_tuning:
            param_grid = {
                'n_estimators': [100, 200, 300],
                'learning_rate': [0.01, 0.1, 0.2],
                'max_depth': [3, 5, 7],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4],
                'subsample': [0.8, 0.9, 1.0]
            }

            gb = GradientBoostingClassifier(random_state=42)
            grid_search = GridSearchCV(
                gb, param_grid, cv=3, scoring='accuracy', n_jobs=-1, verbose=1
            )
            grid_search.fit(X_train, y_train)

            best_model = grid_search.best_estimator_
            logger.info(f"Best GB params: {grid_search.best_params_}")
        else:
            best_model = GradientBoostingClassifier(
                n_estimators=200, learning_rate=0.1, max_depth=5, random_state=42
            )
            best_model.fit(X_train, y_train)

        # Scale features (optional for GB, but consistent)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Retrain on scaled data
        best_model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = best_model.predict(X_test_scaled)
        metrics = self._calculate_metrics(y_test, y_pred)

        # Feature importance
        metrics["feature_importance"] = dict(enumerate(best_model.feature_importances_))

        return best_model, scaler, metrics

    async def _train_ensemble(
        self, X_train: np.ndarray, y_train: np.ndarray,
        X_test: np.ndarray, y_test: np.ndarray,
        hyperparameter_tuning: bool = True
    ) -> Tuple[Any, Any, Dict[str, Any]]:
        """Train ensemble model with multiple algorithms"""

        # Train individual models
        rf_model = RandomForestClassifier(n_estimators=200, max_depth=20, random_state=42, n_jobs=-1)
        gb_model = GradientBoostingClassifier(n_estimators=200, learning_rate=0.1, max_depth=5, random_state=42)

        # Scale features
        scaler = RobustScaler()  # More robust to outliers
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train models
        rf_model.fit(X_train_scaled, y_train)
        gb_model.fit(X_train_scaled, y_train)

        # Create ensemble
        ensemble = VotingClassifier(
            estimators=[('rf', rf_model), ('gb', gb_model)],
            voting='soft'  # Use probability predictions
        )

        ensemble.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = ensemble.predict(X_test_scaled)
        metrics = self._calculate_metrics(y_test, y_pred)

        # Feature importance (average of both models)
        rf_importance = rf_model.feature_importances_
        gb_importance = gb_model.feature_importances_
        avg_importance = (rf_importance + gb_importance) / 2
        metrics["feature_importance"] = dict(enumerate(avg_importance))

        return ensemble, scaler, metrics

    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate comprehensive metrics"""
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, average='weighted')),
            "recall": float(recall_score(y_true, y_pred, average='weighted')),
            "f1_score": float(f1_score(y_true, y_pred, average='weighted'))
        }

    async def predict_signal(
        self,
        features: Dict[str, float],
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make prediction using trained model"""
        try:
            # Load latest active model if not specified
            if not model_name:
                models = await DatabaseService.get_ml_models(active_only=True)
                if not models:
                    raise ValueError("No active models found")
                model_name = models[0]["name"]

            # Load model and scaler
            model_path = self.models_dir / f"{model_name}.pkl"
            scaler_path = self.scalers_dir / f"{model_name}_scaler.pkl"

            if not model_path.exists() or not scaler_path.exists():
                raise FileNotFoundError(f"Model files not found: {model_name}")

            model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)

            # Prepare features
            feature_vector = [
                features.get("rsi_14", 50.0),
                features.get("macd", 0.0),
                features.get("macd_signal", 0.0),
                features.get("macd_hist", 0.0),
                features.get("atr_14", 100.0),
                features.get("adx_14", 25.0),
                features.get("bb_upper", 0.0),
                features.get("bb_middle", 0.0),
                features.get("bb_lower", 0.0),
                features.get("open_interest", 0.0),
                features.get("funding_rate", 0.0),
                features.get("ai_confidence", 0.5)
            ]

            # Scale and predict
            X = np.array([feature_vector])
            X_scaled = scaler.transform(X)

            if hasattr(model, 'predict_proba'):
                probabilities = model.predict_proba(X_scaled)[0]
                prediction = int(model.predict(X_scaled)[0])
                confidence = float(max(probabilities))
            else:
                prediction = int(model.predict(X_scaled)[0])
                confidence = 0.5  # Default confidence for non-probabilistic models

            signal = "LONG" if prediction == 1 else "SHORT"

            return {
                "signal": signal,
                "confidence": confidence,
                "model_used": model_name,
                "probabilities": probabilities.tolist() if 'probabilities' in locals() else None
            }

        except Exception as e:
            logger.error(f"Failed to make prediction: {e}")
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "error": str(e)
            }

# Global instance
advanced_ml_service = AdvancedMLService()