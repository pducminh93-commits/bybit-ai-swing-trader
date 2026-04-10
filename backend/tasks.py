from celery_app import celery_app
from main import _run_backtest_sync
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def run_backtest(self, symbol: str, days: int, leverage: float = 10.0, min_hold_candles: int = 6, stop_loss_pct: float = 0.05):
    """Async backtesting task."""
    try:
        logger.info(f"Starting backtest task for {symbol}, {days} days")
        result = _run_backtest_sync(symbol, days, leverage, min_hold_candles, stop_loss_pct)
        logger.info(f"Completed backtest for {symbol}")
        return result
    except Exception as e:
        logger.error(f"Backtest task failed for {symbol}: {e}")
        raise self.retry(countdown=60, max_retries=3)

@celery_app.task
def train_model(symbol: str, model_type: str = 'rf'):
    """Async model training task."""
    try:
        from main import _run_train_sync  # Assume we create this
        logger.info(f"Starting model training for {symbol}")
        result = _run_train_sync(symbol, model_type)
        logger.info(f"Completed model training for {symbol}")
        return result
    except Exception as e:
        logger.error(f"Training task failed for {symbol}: {e}")
        raise