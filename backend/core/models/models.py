from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, Dict, Any
from core.database.config import Base

class BacktestResult(Base):
    """Model for backtest results"""
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    strategy_name = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_balance = Column(Float, nullable=False)
    final_balance = Column(Float, nullable=False)
    total_return_pct = Column(Float, nullable=False)
    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=False)
    losing_trades = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)
    profit_factor = Column(Float, nullable=False)
    max_drawdown_pct = Column(Float, nullable=False)
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    avg_win_pct = Column(Float, nullable=True)
    avg_loss_pct = Column(Float, nullable=True)
    largest_win_pct = Column(Float, nullable=True)
    largest_loss_pct = Column(Float, nullable=True)
    avg_holding_period = Column(Float, nullable=True)  # in candles
    max_holding_period = Column(Float, nullable=True)
    leverage = Column(Float, nullable=False, default=1.0)
    stop_loss_pct = Column(Float, nullable=False, default=0.05)
    min_hold_candles = Column(Integer, nullable=False, default=6)

    # Configuration parameters
    config = Column(JSON, nullable=True)  # Store strategy configuration

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to trades
    trades = relationship("Trade", back_populates="backtest", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "initial_balance": self.initial_balance,
            "final_balance": self.final_balance,
            "total_return_pct": self.total_return_pct,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "max_drawdown_pct": self.max_drawdown_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "avg_win_pct": self.avg_win_pct,
            "avg_loss_pct": self.avg_loss_pct,
            "largest_win_pct": self.largest_win_pct,
            "largest_loss_pct": self.largest_loss_pct,
            "avg_holding_period": self.avg_holding_period,
            "max_holding_period": self.max_holding_period,
            "leverage": self.leverage,
            "stop_loss_pct": self.stop_loss_pct,
            "min_hold_candles": self.min_hold_candles,
            "config": self.config,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class Trade(Base):
    """Model for individual trades within a backtest"""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    backtest_id = Column(Integer, ForeignKey("backtest_results.id"), nullable=False, index=True)

    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # 'LONG' or 'SHORT'
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    leverage = Column(Float, nullable=False, default=1.0)
    realized_pnl = Column(Float, nullable=False)
    realized_pnl_pct = Column(Float, nullable=False)
    holding_period = Column(Integer, nullable=False)  # in candles
    entry_reason = Column(Text, nullable=True)
    exit_reason = Column(Text, nullable=True)

    # Risk management
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    max_adverse_excursion = Column(Float, nullable=True)  # MAE
    max_favorable_excursion = Column(Float, nullable=True)  # MFE

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    backtest = relationship("BacktestResult", back_populates="trades")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "backtest_id": self.backtest_id,
            "symbol": self.symbol,
            "side": self.side,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat(),
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "leverage": self.leverage,
            "realized_pnl": self.realized_pnl,
            "realized_pnl_pct": self.realized_pnl_pct,
            "holding_period": self.holding_period,
            "entry_reason": self.entry_reason,
            "exit_reason": self.exit_reason,
            "stop_loss_price": self.stop_loss_price,
            "take_profit_price": self.take_profit_price,
            "max_adverse_excursion": self.max_adverse_excursion,
            "max_favorable_excursion": self.max_favorable_excursion,
            "created_at": self.created_at.isoformat(),
        }

class Signal(Base):
    """Model for trading signals"""
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(10), nullable=False)  # 'BUY', 'SELL', 'HOLD'
    confidence = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)

    # Signal details
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)

    # Technical indicators
    rsi_14 = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_hist = Column(Float, nullable=True)
    atr_14 = Column(Float, nullable=True)
    adx_14 = Column(Float, nullable=True)
    bb_upper = Column(Float, nullable=True)
    bb_middle = Column(Float, nullable=True)
    bb_lower = Column(Float, nullable=True)

    # Market data
    open_interest = Column(Float, nullable=True)
    funding_rate = Column(Float, nullable=True)

    # AI confidence and risk metrics
    ai_confidence = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    is_extreme_funding = Column(Boolean, default=False)

    # Source (backtest, live, demo)
    source = Column(String(20), nullable=False, default="backtest")

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "reason": self.reason,
            "rsi_14": self.rsi_14,
            "macd": self.macd,
            "macd_signal": self.macd_signal,
            "macd_hist": self.macd_hist,
            "atr_14": self.atr_14,
            "adx_14": self.adx_14,
            "bb_upper": self.bb_upper,
            "bb_middle": self.bb_middle,
            "bb_lower": self.bb_lower,
            "open_interest": self.open_interest,
            "funding_rate": self.funding_rate,
            "ai_confidence": self.ai_confidence,
            "risk_score": self.risk_score,
            "is_extreme_funding": self.is_extreme_funding,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
        }

class MLModel(Base):
    """Model for storing ML model metadata and performance"""
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    model_type = Column(String(50), nullable=False)  # 'rf', 'gb', 'ensemble', 'universal'
    symbols = Column(JSON, nullable=True)  # List of symbols model was trained on
    accuracy = Column(Float, nullable=True)
    feature_importance = Column(JSON, nullable=True)
    model_path = Column(String(255), nullable=False)  # Path to saved model file
    scaler_path = Column(String(255), nullable=True)  # Path to saved scaler file

    # Training metadata
    trained_at = Column(DateTime, nullable=False)
    training_duration = Column(Float, nullable=True)  # in seconds
    training_samples = Column(Integer, nullable=True)
    validation_accuracy = Column(Float, nullable=True)

    # Model status
    is_active = Column(Boolean, default=True)
    version = Column(String(20), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "model_type": self.model_type,
            "symbols": self.symbols,
            "accuracy": self.accuracy,
            "feature_importance": self.feature_importance,
            "model_path": self.model_path,
            "scaler_path": self.scaler_path,
            "trained_at": self.trained_at.isoformat(),
            "training_duration": self.training_duration,
            "training_samples": self.training_samples,
            "validation_accuracy": self.validation_accuracy,
            "is_active": self.is_active,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }