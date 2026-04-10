"""
Common utilities for signal generation across AI and ML models.
Reduces code duplication between ai_model.py and ml_model.py.
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SignalUtils:
    """Utility class for signal-related calculations."""

    @staticmethod
    def calculate_confidence(bullish_signals: int, bearish_signals: int, total_signals: int = 8) -> float:
        """
        Calculate confidence based on signal counts.
        Args:
            bullish_signals: Number of bullish indicators
            bearish_signals: Number of bearish indicators
            total_signals: Total possible signals
        Returns:
            Confidence score between 0 and 1
        """
        if total_signals == 0:
            return 0.0

        signal_strength = bullish_signals - bearish_signals
        confidence = abs(signal_strength) / total_signals

        # Cap at 1.0 and ensure minimum for decision
        return min(max(confidence, 0.0), 1.0)

    @staticmethod
    def apply_hysteresis(current_signal: str, last_signal: Optional[str],
                        confidence: float, min_change: float = 0.15) -> str:
        """
        Apply hysteresis to prevent signal flipping.
        Args:
            current_signal: New signal ('LONG', 'SHORT', 'HOLD')
            last_signal: Previous signal
            confidence: Current confidence
            min_change: Minimum confidence change required
        Returns:
            Final signal after hysteresis
        """
        if not last_signal or last_signal == 'HOLD':
            return current_signal

        # Require significant confidence change to switch directions
        if current_signal != last_signal and confidence < min_change:
            logger.debug(f"Hysteresis: Keeping {last_signal}, confidence {confidence} < {min_change}")
            return last_signal

        return current_signal

    @staticmethod
    def validate_indicators(indicators: Dict[str, Any]) -> bool:
        """
        Validate that required indicators are present and valid.
        Returns True if all required indicators are available.
        """
        required = ['rsi', 'macd', 'bb_upper', 'bb_lower', 'stoch_k', 'stoch_d']
        for req in required:
            if req not in indicators or indicators[req] is None:
                logger.warning(f"Missing required indicator: {req}")
                return False
        return True

    @staticmethod
    def normalize_signal(signal: str) -> str:
        """Normalize signal strings to standard format."""
        signal_map = {
            'BUY': 'LONG',
            'SELL': 'SHORT',
            'buy': 'LONG',
            'sell': 'SHORT'
        }
        return signal_map.get(signal, signal.upper())