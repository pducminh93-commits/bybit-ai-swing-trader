"""
Model Manager for optimized ML model loading with singleton pattern.
Preloads models on startup to reduce latency.
"""

import pickle
import os
from typing import Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ModelManager:
    """Singleton manager for ML models with caching."""

    _instance = None
    _models: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.models_dir = Path("../models")
            self._preload_models()

    def _preload_models(self):
        """Preload all available models on startup."""
        if not self.models_dir.exists():
            logger.warning("Models directory not found, skipping preload")
            return

        for model_file in self.models_dir.glob("*_model.pkl"):
            try:
                symbol = model_file.stem.replace("_model", "").replace("_", "")
                with open(model_file, 'rb') as f:
                    model = pickle.load(f)
                self._models[symbol] = model
                logger.info(f"Preloaded model for {symbol}")
            except Exception as e:
                logger.error(f"Failed to preload model {model_file}: {e}")

    def get_model(self, symbol: str) -> Optional[Any]:
        """Get model for symbol, load from disk if not cached."""
        if symbol in self._models:
            return self._models[symbol]

        # Try to load from disk
        model_path = self.models_dir / f"{symbol}_model.pkl"
        if model_path.exists():
            try:
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                self._models[symbol] = model
                logger.info(f"Loaded model for {symbol} from disk")
                return model
            except Exception as e:
                logger.error(f"Failed to load model for {symbol}: {e}")
                return None

        logger.warning(f"No model found for {symbol}")
        return None

    def save_model(self, symbol: str, model: Any):
        """Save model to disk and cache."""
        self.models_dir.mkdir(exist_ok=True)
        model_path = self.models_dir / f"{symbol}_model.pkl"
        try:
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            self._models[symbol] = model
            logger.info(f"Saved model for {symbol}")
        except Exception as e:
            logger.error(f"Failed to save model for {symbol}: {e}")

    def clear_cache(self, symbol: Optional[str] = None):
        """Clear model cache."""
        if symbol:
            self._models.pop(symbol, None)
            logger.info(f"Cleared cache for {symbol}")
        else:
            self._models.clear()
            logger.info("Cleared all model caches")