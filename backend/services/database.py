"""
Database models and utilities using SQLAlchemy with SQLite.
Provides persistence for trades, models, and backtests.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime
from typing import List, Dict, Any

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20))
    type = Column(String(20))  # LONG, SHORT, CLOSE_LONG, etc.
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    profit = Column(Float)
    size = Column(Float)
    timestamp = Column(DateTime)
    reason = Column(String(255))
    backtest_id = Column(String(50), nullable=True)

class BacktestResult(Base):
    __tablename__ = 'backtests'

    id = Column(String(50), primary_key=True)
    symbol = Column(String(20))
    days = Column(Integer)
    total_return = Column(Float)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    max_drawdown = Column(Float)
    total_trades = Column(Integer)
    timestamp = Column(DateTime)
    metrics = Column(JSON)  # Store full metrics as JSON

class ModelMetadata(Base):
    __tablename__ = 'models'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20))
    model_type = Column(String(20))
    accuracy = Column(Float)
    feature_importance = Column(JSON)
    created_at = Column(DateTime)

class DatabaseManager:
    """Manager for database operations."""

    def __init__(self, db_path: str = "backend/trading.db"):
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def save_trades(self, trades: List[Dict[str, Any]], backtest_id: str = None):
        """Save trades to database."""
        session = self.SessionLocal()
        try:
            for trade in trades:
                db_trade = Trade(
                    symbol=trade.get('symbol', 'UNKNOWN'),
                    type=trade['type'],
                    entry_price=trade.get('entry_price', 0),
                    exit_price=trade.get('exit_price'),
                    profit=trade['profit'],
                    size=trade.get('size', 0),
                    timestamp=datetime.fromtimestamp(int(trade['timestamp']) / 1000),
                    reason=trade.get('reason', ''),
                    backtest_id=backtest_id
                )
                session.add(db_trade)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def save_backtest(self, backtest_data: Dict[str, Any], backtest_id: str):
        """Save backtest result to database."""
        session = self.SessionLocal()
        try:
            db_backtest = BacktestResult(
                id=backtest_id,
                symbol=backtest_data.get('symbol', 'UNKNOWN'),
                days=backtest_data.get('days', 30),
                total_return=backtest_data.get('total_return', 0),
                win_rate=backtest_data.get('win_rate', 0),
                profit_factor=backtest_data.get('profit_factor', 0),
                max_drawdown=backtest_data.get('max_drawdown', 0),
                total_trades=backtest_data.get('total_trades', 0),
                timestamp=datetime.utcnow(),
                metrics=json.dumps(backtest_data.get('metrics', {}))
            )
            session.add(db_backtest)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_recent_backtests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent backtest results."""
        session = self.SessionLocal()
        try:
            results = session.query(BacktestResult).order_by(BacktestResult.timestamp.desc()).limit(limit).all()
            return [{
                'id': r.id,
                'symbol': r.symbol,
                'days': r.days,
                'total_return': r.total_return,
                'win_rate': r.win_rate,
                'profit_factor': r.profit_factor,
                'max_drawdown': r.max_drawdown,
                'total_trades': r.total_trades,
                'timestamp': r.timestamp.isoformat(),
                'metrics': json.loads(r.metrics)
            } for r in results]
        finally:
            session.close()

    def get_trades_for_backtest(self, backtest_id: str) -> List[Dict[str, Any]]:
        """Get trades for a specific backtest."""
        session = self.SessionLocal()
        try:
            trades = session.query(Trade).filter(Trade.backtest_id == backtest_id).order_by(Trade.timestamp).all()
            return [{
                'id': t.id,
                'symbol': t.symbol,
                'type': t.type,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'profit': t.profit,
                'size': t.size,
                'timestamp': int(t.timestamp.timestamp() * 1000),
                'reason': t.reason
            } for t in trades]
        finally:
            session.close()