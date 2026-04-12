from typing import List, Dict, Any, Optional
from sqlalchemy import select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import json

from core.database.config import db
from core.models.models import BacktestResult, Trade, Signal, MLModel

class DatabaseService:
    """Service for database operations"""

    @staticmethod
    async def save_backtest_result(backtest_data: Dict[str, Any], symbol: str) -> int:
        """Save backtest result to database"""
        async with db.async_session() as session:
            try:
                # Create backtest result record
                backtest = BacktestResult(
                    symbol=symbol,
                    strategy_name=backtest_data.get('strategy_name', 'AI Swing Trader'),
                    start_date=datetime.fromisoformat(backtest_data['start_date']) if isinstance(backtest_data.get('start_date'), str) else backtest_data.get('start_date'),
                    end_date=datetime.fromisoformat(backtest_data['end_date']) if isinstance(backtest_data.get('end_date'), str) else backtest_data.get('end_date'),
                    initial_balance=backtest_data['initial_balance'],
                    final_balance=backtest_data['final_balance'],
                    total_return_pct=backtest_data['total_return_pct'],
                    total_trades=backtest_data['total_trades'],
                    winning_trades=backtest_data['winning_trades'],
                    losing_trades=backtest_data['losing_trades'],
                    win_rate=backtest_data['win_rate'],
                    profit_factor=backtest_data['profit_factor'],
                    max_drawdown_pct=backtest_data['max_drawdown_pct'],
                    sharpe_ratio=backtest_data.get('sharpe_ratio'),
                    sortino_ratio=backtest_data.get('sortino_ratio'),
                    avg_win_pct=backtest_data.get('avg_win_pct'),
                    avg_loss_pct=backtest_data.get('avg_loss_pct'),
                    largest_win_pct=backtest_data.get('largest_win_pct'),
                    largest_loss_pct=backtest_data.get('largest_loss_pct'),
                    avg_holding_period=backtest_data.get('avg_holding_period'),
                    max_holding_period=backtest_data.get('max_holding_period'),
                    leverage=backtest_data.get('leverage', 1.0),
                    stop_loss_pct=backtest_data.get('stop_loss_pct', 0.05),
                    min_hold_candles=backtest_data.get('min_hold_candles', 6),
                    config=backtest_data.get('config')
                )

                session.add(backtest)
                await session.flush()  # Get the ID

                # Save trades if available
                if 'trades' in backtest_data and backtest_data['trades']:
                    for trade_data in backtest_data['trades']:
                        trade = Trade(
                            backtest_id=backtest.id,
                            symbol=trade_data['symbol'],
                            side=trade_data['side'],
                            entry_time=datetime.fromisoformat(trade_data['entry_time']) if isinstance(trade_data.get('entry_time'), str) else trade_data.get('entry_time'),
                            exit_time=datetime.fromisoformat(trade_data['exit_time']) if isinstance(trade_data.get('exit_time'), str) else trade_data.get('exit_time'),
                            entry_price=trade_data['entry_price'],
                            exit_price=trade_data['exit_price'],
                            quantity=trade_data['quantity'],
                            leverage=trade_data.get('leverage', 1.0),
                            realized_pnl=trade_data['realized_pnl'],
                            realized_pnl_pct=trade_data['realized_pnl_pct'],
                            holding_period=trade_data['holding_period'],
                            entry_reason=trade_data.get('entry_reason'),
                            exit_reason=trade_data.get('exit_reason'),
                            stop_loss_price=trade_data.get('stop_loss_price'),
                            take_profit_price=trade_data.get('take_profit_price'),
                            max_adverse_excursion=trade_data.get('max_adverse_excursion'),
                            max_favorable_excursion=trade_data.get('max_favorable_excursion')
                        )
                        session.add(trade)

                await session.commit()
                return backtest.id

            except Exception as e:
                await session.rollback()
                raise e

    @staticmethod
    async def get_backtest_results(symbol: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get backtest results from database"""
        async with db.async_session() as session:
            try:
                query = select(BacktestResult).order_by(desc(BacktestResult.created_at))

                if symbol:
                    query = query.where(BacktestResult.symbol == symbol)

                query = query.limit(limit)
                result = await session.execute(query)
                backtests = result.scalars().all()

                return [backtest.to_dict() for backtest in backtests]

            except Exception as e:
                raise e

    @staticmethod
    async def get_backtest_by_id(backtest_id: int) -> Optional[Dict[str, Any]]:
        """Get specific backtest by ID with trades"""
        async with db.async_session() as session:
            try:
                # Get backtest
                query = select(BacktestResult).where(BacktestResult.id == backtest_id)
                result = await session.execute(query)
                backtest = result.scalar_one_or_none()

                if not backtest:
                    return None

                backtest_dict = backtest.to_dict()

                # Get trades
                trades_query = select(Trade).where(Trade.backtest_id == backtest_id)
                trades_result = await session.execute(trades_query)
                trades = trades_result.scalars().all()
                backtest_dict['trades'] = [trade.to_dict() for trade in trades]

                return backtest_dict

            except Exception as e:
                raise e

    @staticmethod
    async def save_signal(signal_data: Dict[str, Any]) -> int:
        """Save trading signal to database"""
        async with db.async_session() as session:
            try:
                signal = Signal(
                    symbol=signal_data['symbol'],
                    signal_type=signal_data['signal'],
                    confidence=signal_data['confidence'],
                    timestamp=datetime.fromisoformat(signal_data['timestamp']) if isinstance(signal_data.get('timestamp'), str) else signal_data.get('timestamp', datetime.utcnow()),
                    entry_price=signal_data.get('entry_price'),
                    stop_loss=signal_data.get('stop_loss'),
                    take_profit=signal_data.get('take_profit'),
                    reason=signal_data.get('reason'),
                    rsi_14=signal_data.get('indicators', {}).get('rsi'),
                    macd=signal_data.get('indicators', {}).get('macd'),
                    macd_signal=signal_data.get('indicators', {}).get('macd_signal'),
                    macd_hist=signal_data.get('indicators', {}).get('macd_hist'),
                    atr_14=signal_data.get('indicators', {}).get('atr'),
                    adx_14=signal_data.get('indicators', {}).get('adx'),
                    bb_upper=signal_data.get('indicators', {}).get('bb_upper'),
                    bb_middle=signal_data.get('indicators', {}).get('bb_middle'),
                    bb_lower=signal_data.get('indicators', {}).get('bb_lower'),
                    ai_confidence=signal_data.get('confidence'),
                    source=signal_data.get('source', 'backtest')
                )

                session.add(signal)
                await session.commit()
                return signal.id

            except Exception as e:
                await session.rollback()
                raise e

    @staticmethod
    async def get_signals(symbol: Optional[str] = None, limit: int = 100, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent signals from database"""
        async with db.async_session() as session:
            try:
                query = select(Signal).where(
                    Signal.timestamp >= datetime.utcnow() - timedelta(hours=hours)
                ).order_by(desc(Signal.timestamp))

                if symbol:
                    query = query.where(Signal.symbol == symbol)

                query = query.limit(limit)
                result = await session.execute(query)
                signals = result.scalars().all()

                return [signal.to_dict() for signal in signals]

            except Exception as e:
                raise e

    @staticmethod
    async def save_ml_model(model_data: Dict[str, Any]) -> int:
        """Save ML model metadata to database"""
        async with db.async_session() as session:
            try:
                # Deactivate previous active model of same type
                if model_data.get('is_active', True):
                    await session.execute(
                        select(MLModel).where(
                            and_(
                                MLModel.model_type == model_data['model_type'],
                                MLModel.is_active == True
                            )
                        )
                    )
                    # Note: In real implementation, you'd update these to inactive

                model = MLModel(
                    name=model_data['name'],
                    model_type=model_data['model_type'],
                    symbols=model_data.get('symbols'),
                    accuracy=model_data.get('accuracy'),
                    feature_importance=model_data.get('feature_importance'),
                    model_path=model_data['model_path'],
                    scaler_path=model_data.get('scaler_path'),
                    trained_at=model_data.get('trained_at', datetime.utcnow()),
                    training_duration=model_data.get('training_duration'),
                    training_samples=model_data.get('training_samples'),
                    validation_accuracy=model_data.get('validation_accuracy'),
                    is_active=model_data.get('is_active', True),
                    version=model_data.get('version')
                )

                session.add(model)
                await session.commit()
                return model.id

            except Exception as e:
                await session.rollback()
                raise e

    @staticmethod
    async def get_ml_models(active_only: bool = False) -> List[Dict[str, Any]]:
        """Get ML models from database"""
        async with db.async_session() as session:
            try:
                query = select(MLModel).order_by(desc(MLModel.trained_at))

                if active_only:
                    query = query.where(MLModel.is_active == True)

                result = await session.execute(query)
                models = result.scalars().all()

                return [model.to_dict() for model in models]

            except Exception as e:
                raise e

    @staticmethod
    async def get_statistics() -> Dict[str, Any]:
        """Get database statistics"""
        async with db.async_session() as session:
            try:
                # Backtest statistics
                backtest_count = await session.execute(
                    select(func.count()).select_from(BacktestResult)
                )
                backtest_count = backtest_count.scalar()

                # Trade statistics
                trade_count = await session.execute(
                    select(func.count()).select_from(Trade)
                )
                trade_count = trade_count.scalar()

                # Signal statistics
                signal_count = await session.execute(
                    select(func.count()).select_from(Signal)
                )
                signal_count = signal_count.scalar()

                # Recent backtest performance
                recent_backtests = await session.execute(
                    select(BacktestResult).order_by(desc(BacktestResult.created_at)).limit(10)
                )
                recent_backtests = recent_backtests.scalars().all()

                avg_win_rate = sum(b.win_rate for b in recent_backtests) / len(recent_backtests) if recent_backtests else 0
                avg_return = sum(b.total_return_pct for b in recent_backtests) / len(recent_backtests) if recent_backtests else 0

                return {
                    "total_backtests": backtest_count,
                    "total_trades": trade_count,
                    "total_signals": signal_count,
                    "recent_performance": {
                        "avg_win_rate": round(avg_win_rate * 100, 2),
                        "avg_return_pct": round(avg_return, 2),
                        "backtest_count": len(recent_backtests)
                    }
                }

            except Exception as e:
                raise e