from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from core.logging.config import get_logger
from infrastructure.database_service import DatabaseService

logger = get_logger("analytics")

class AnalyticsService:
    """Advanced analytics and reporting service for trading performance"""

    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes

    async def generate_portfolio_analytics(
        self,
        symbol: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Generate comprehensive portfolio analytics"""
        try:
            # Get backtests and trades data
            backtests = await DatabaseService.get_backtest_results(symbol, limit=100)
            all_trades = []

            for backtest in backtests:
                if 'id' in backtest:
                    detailed_backtest = await DatabaseService.get_backtest_by_id(backtest['id'])
                    if detailed_backtest and 'trades' in detailed_backtest:
                        all_trades.extend(detailed_backtest['trades'])

            if not all_trades:
                return {"error": "No trading data available for analysis"}

            # Convert to DataFrame for analysis
            trades_df = pd.DataFrame(all_trades)

            # Basic metrics
            basic_metrics = self._calculate_basic_metrics(trades_df)

            # Risk metrics
            risk_metrics = self._calculate_risk_metrics(trades_df)

            # Performance metrics
            performance_metrics = self._calculate_performance_metrics(trades_df)

            # Time-based analysis
            time_analysis = self._analyze_time_patterns(trades_df)

            # Symbol performance
            symbol_performance = self._analyze_symbol_performance(trades_df)

            # Trade quality analysis
            trade_quality = self._analyze_trade_quality(trades_df)

            return {
                "summary": {
                    "total_trades": len(trades_df),
                    "analysis_period_days": days,
                    "data_points": len(all_trades),
                    "symbols_analyzed": len(symbol_performance) if symbol_performance else 0
                },
                "basic_metrics": basic_metrics,
                "risk_metrics": risk_metrics,
                "performance_metrics": performance_metrics,
                "time_analysis": time_analysis,
                "symbol_performance": symbol_performance,
                "trade_quality": trade_quality,
                "recommendations": self._generate_recommendations(
                    basic_metrics, risk_metrics, performance_metrics
                )
            }

        except Exception as e:
            logger.error(f"Failed to generate portfolio analytics: {e}")
            return {"error": str(e)}

    def _calculate_basic_metrics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate basic trading metrics"""
        try:
            winning_trades = trades_df[trades_df['realized_pnl'] > 0]
            losing_trades = trades_df[trades_df['realized_pnl'] < 0]

            return {
                "total_trades": len(trades_df),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0,
                "total_pnl": float(trades_df['realized_pnl'].sum()),
                "total_pnl_pct": float(trades_df['realized_pnl_pct'].sum()),
                "avg_trade_pnl": float(trades_df['realized_pnl'].mean()),
                "avg_trade_pnl_pct": float(trades_df['realized_pnl_pct'].mean()),
                "largest_win": float(trades_df['realized_pnl'].max()) if len(winning_trades) > 0 else 0,
                "largest_loss": float(trades_df['realized_pnl'].min()) if len(losing_trades) > 0 else 0,
                "avg_win": float(winning_trades['realized_pnl'].mean()) if len(winning_trades) > 0 else 0,
                "avg_loss": float(losing_trades['realized_pnl'].mean()) if len(losing_trades) > 0 else 0
            }
        except Exception as e:
            logger.warning(f"Failed to calculate basic metrics: {e}")
            return {}

    def _calculate_risk_metrics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate risk-related metrics"""
        try:
            if len(trades_df) < 2:
                return {"error": "Insufficient data for risk analysis"}

            pnls = trades_df['realized_pnl'].values

            # Sharpe ratio (assuming daily returns, risk-free rate = 0)
            returns = pnls / 1000  # Normalize to capital
            if len(returns) > 1:
                sharpe_ratio = float(np.mean(returns) / np.std(returns, ddof=1)) if np.std(returns, ddof=1) > 0 else 0
            else:
                sharpe_ratio = 0

            # Sortino ratio (downside deviation)
            downside_returns = returns[returns < 0]
            if len(downside_returns) > 0:
                sortino_ratio = float(np.mean(returns) / np.std(downside_returns, ddof=1)) if np.std(downside_returns, ddof=1) > 0 else 0
            else:
                sortino_ratio = float('inf')  # No downside risk

            # Maximum drawdown
            cumulative = np.cumsum(returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = running_max - cumulative
            max_drawdown = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0

            # Calmar ratio
            calmar_ratio = float(np.mean(returns) / max_drawdown) if max_drawdown > 0 else float('inf')

            # Value at Risk (95% confidence)
            var_95 = float(np.percentile(returns, 5))

            return {
                "sharpe_ratio": sharpe_ratio,
                "sortino_ratio": sortino_ratio,
                "max_drawdown": max_drawdown,
                "calmar_ratio": calmar_ratio,
                "value_at_risk_95": var_95,
                "volatility": float(np.std(returns, ddof=1)),
                "skewness": float(pd.Series(returns).skew()),
                "kurtosis": float(pd.Series(returns).kurtosis())
            }
        except Exception as e:
            logger.warning(f"Failed to calculate risk metrics: {e}")
            return {}

    def _calculate_performance_metrics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate advanced performance metrics"""
        try:
            # Profit factor
            winning_trades = trades_df[trades_df['realized_pnl'] > 0]
            losing_trades = trades_df[trades_df['realized_pnl'] < 0]

            total_wins = winning_trades['realized_pnl'].sum()
            total_losses = abs(losing_trades['realized_pnl'].sum())

            profit_factor = float(total_wins / total_losses) if total_losses > 0 else float('inf')

            # Recovery factor (net profit / max drawdown)
            # This would require equity curve analysis

            # Payoff ratio (avg win / avg loss)
            avg_win = winning_trades['realized_pnl'].mean() if len(winning_trades) > 0 else 0
            avg_loss = abs(losing_trades['realized_pnl'].mean()) if len(losing_trades) > 0 else 0
            payoff_ratio = float(avg_win / avg_loss) if avg_loss > 0 else float('inf')

            # Win/loss ratio
            win_loss_ratio = len(winning_trades) / len(losing_trades) if len(losing_trades) > 0 else float('inf')

            # Expectancy
            win_rate = len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0
            loss_rate = 1 - win_rate
            expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)

            return {
                "profit_factor": profit_factor,
                "payoff_ratio": payoff_ratio,
                "win_loss_ratio": win_loss_ratio,
                "expectancy": float(expectancy),
                "kelly_criterion": self._calculate_kelly_criterion(win_rate, avg_win, avg_loss),
                "optimal_f": self._calculate_optimal_f(win_rate, avg_win, avg_loss)
            }
        except Exception as e:
            logger.warning(f"Failed to calculate performance metrics: {e}")
            return {}

    def _calculate_kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calculate Kelly Criterion"""
        try:
            if avg_loss == 0:
                return 0
            kelly = win_rate - ((1 - win_rate) / (avg_win / avg_loss))
            return max(0, float(kelly))  # Kelly can be negative
        except:
            return 0

    def _calculate_optimal_f(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calculate Optimal f (fraction of capital to risk)"""
        try:
            if avg_loss == 0:
                return 0
            optimal_f = ((win_rate * avg_win) - ((1 - win_rate) * avg_loss)) / avg_win
            return max(0, float(optimal_f))
        except:
            return 0

    def _analyze_time_patterns(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze time-based patterns in trading"""
        try:
            if 'entry_time' not in trades_df.columns:
                return {"error": "No time data available"}

            # Convert to datetime if needed
            trades_df = trades_df.copy()
            trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])

            # Hourly analysis
            hourly_performance = trades_df.groupby(trades_df['entry_time'].dt.hour)['realized_pnl'].agg(['mean', 'count', 'sum'])

            # Daily analysis
            daily_performance = trades_df.groupby(trades_df['entry_time'].dt.dayofweek)['realized_pnl'].agg(['mean', 'count', 'sum'])

            # Best/worst hours
            best_hour = int(hourly_performance['mean'].idxmax()) if len(hourly_performance) > 0 else None
            worst_hour = int(hourly_performance['mean'].idxmin()) if len(hourly_performance) > 0 else None

            # Best/worst days
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            best_day = day_names[int(daily_performance['mean'].idxmax())] if len(daily_performance) > 0 else None
            worst_day = day_names[int(daily_performance['mean'].idxmin())] if len(daily_performance) > 0 else None

            return {
                "best_trading_hour": best_hour,
                "worst_trading_hour": worst_hour,
                "best_trading_day": best_day,
                "worst_trading_day": worst_day,
                "hourly_performance": hourly_performance.to_dict('index'),
                "daily_performance": {day_names[k]: v for k, v in daily_performance.to_dict('index').items()}
            }
        except Exception as e:
            logger.warning(f"Failed to analyze time patterns: {e}")
            return {}

    def _analyze_symbol_performance(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze performance by symbol"""
        try:
            if 'symbol' not in trades_df.columns:
                return {}

            symbol_stats = trades_df.groupby('symbol').agg({
                'realized_pnl': ['count', 'sum', 'mean', 'std'],
                'realized_pnl_pct': ['mean', 'std']
            }).round(4)

            # Flatten column names
            symbol_stats.columns = ['_'.join(col).strip() for col in symbol_stats.columns.values]
            symbol_stats = symbol_stats.reset_index()

            # Sort by total profit
            symbol_stats = symbol_stats.sort_values('realized_pnl_sum', ascending=False)

            return symbol_stats.to_dict('records')
        except Exception as e:
            logger.warning(f"Failed to analyze symbol performance: {e}")
            return {}

    def _analyze_trade_quality(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze trade quality metrics"""
        try:
            # Holding period analysis
            if 'holding_period' in trades_df.columns:
                avg_holding_period = float(trades_df['holding_period'].mean())
                median_holding_period = float(trades_df['holding_period'].median())
                max_holding_period = int(trades_df['holding_period'].max())
            else:
                avg_holding_period = median_holding_period = max_holding_period = 0

            # Trade size analysis
            if 'quantity' in trades_df.columns:
                avg_quantity = float(trades_df['quantity'].mean())
                median_quantity = float(trades_df['quantity'].median())
            else:
                avg_quantity = median_quantity = 0

            # Risk management analysis
            risk_reward_ratios = []
            for _, trade in trades_df.iterrows():
                if trade.get('stop_loss_price') and trade.get('take_profit_price') and trade.get('entry_price'):
                    entry = trade['entry_price']
                    if trade.get('side') == 'LONG':
                        risk = entry - trade['stop_loss_price']
                        reward = trade['take_profit_price'] - entry
                    else:  # SHORT
                        risk = trade['stop_loss_price'] - entry
                        reward = entry - trade['take_profit_price']

                    if risk > 0:
                        risk_reward_ratios.append(reward / risk)

            avg_risk_reward = float(np.mean(risk_reward_ratios)) if risk_reward_ratios else 0

            return {
                "avg_holding_period": avg_holding_period,
                "median_holding_period": median_holding_period,
                "max_holding_period": max_holding_period,
                "avg_quantity": avg_quantity,
                "median_quantity": median_quantity,
                "avg_risk_reward_ratio": avg_risk_reward,
                "risk_reward_distribution": {
                    "good_trades": len([r for r in risk_reward_ratios if r >= 2]),  # 1:2 or better
                    "acceptable_trades": len([r for r in risk_reward_ratios if 1 <= r < 2]),  # 1:1 to 1:2
                    "poor_trades": len([r for r in risk_reward_ratios if r < 1])  # Less than 1:1
                }
            }
        except Exception as e:
            logger.warning(f"Failed to analyze trade quality: {e}")
            return {}

    def _generate_recommendations(
        self,
        basic_metrics: Dict,
        risk_metrics: Dict,
        performance_metrics: Dict
    ) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []

        try:
            # Win rate recommendations
            win_rate = basic_metrics.get('win_rate', 0)
            if win_rate < 0.4:
                recommendations.append("Consider improving entry signals - win rate is below 40%")
            elif win_rate > 0.7:
                recommendations.append("Excellent win rate - focus on position sizing and risk management")

            # Profit factor recommendations
            profit_factor = performance_metrics.get('profit_factor', 0)
            if profit_factor < 1.5:
                recommendations.append("Profit factor below 1.5 - review risk management and cut losses earlier")
            elif profit_factor > 2.5:
                recommendations.append("Strong profit factor - consider increasing position sizes")

            # Risk recommendations
            sharpe_ratio = risk_metrics.get('sharpe_ratio', 0)
            if sharpe_ratio < 1:
                recommendations.append("Sharpe ratio below 1 - strategy shows poor risk-adjusted returns")
            elif sharpe_ratio > 2:
                recommendations.append("Excellent Sharpe ratio - strategy performs well in varying conditions")

            # Drawdown recommendations
            max_drawdown = risk_metrics.get('max_drawdown', 0)
            if max_drawdown > 0.2:  # 20%
                recommendations.append("High maximum drawdown - implement stricter risk limits")
            elif max_drawdown < 0.05:  # 5%
                recommendations.append("Low drawdown - consider if position sizes are too conservative")

            # Kelly criterion recommendations
            kelly = performance_metrics.get('kelly_criterion', 0)
            if kelly > 0.1:
                recommendations.append(".1f"            elif kelly < 0:
                recommendations.append("Negative Kelly criterion - avoid using this strategy")

            # Default recommendations
            if not recommendations:
                recommendations.append("Strategy shows balanced performance - continue monitoring")
                recommendations.append("Consider paper trading new variations before live deployment")

        except Exception as e:
            logger.warning(f"Failed to generate recommendations: {e}")
            recommendations.append("Unable to generate specific recommendations due to analysis errors")

        return recommendations

# Global instance
analytics_service = AnalyticsService()