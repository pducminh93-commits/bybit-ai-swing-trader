import pandas as pd
import numpy as np
import talib as ta
from typing import Dict, List, Any, Optional
from services.bybit_service import BybitService
from services.ta_analysis import TechnicalAnalysis

class MultiTimeframeAnalysis:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.timeframes = {
            '1h': '60',    # 1 hour
            '4h': '240',   # 4 hours (current)
            '1d': 'D'      # 1 day
        }
        self.analyses = {}

    def analyze_all_timeframes(self) -> Dict[str, Dict[str, Any]]:
        """Analyze symbol across multiple timeframes"""
        results = {}

        for tf_name, interval in self.timeframes.items():
            try:
                # Fetch data for this timeframe
                if interval == 'D':
                    # Bybit uses 'D' for daily
                    data = BybitService.fetch_klines(self.symbol, interval='D', limit=100)
                else:
                    data = BybitService.fetch_klines(self.symbol, interval=interval, limit=200)

                if data.get('retCode') == 0:
                    klines = data['result']['list']
                    ta_analysis = TechnicalAnalysis(klines)
                    indicators = ta_analysis.calculate_indicators()
                    current_price = ta_analysis.get_latest_price()

                    # Generate signal for this timeframe
                    from services.ai_model import AISignalGenerator
                    ai_gen = AISignalGenerator()
                    signal = ai_gen.generate_signal(indicators, current_price, f"{self.symbol}_{tf_name}")

                    results[tf_name] = {
                        'indicators': indicators,
                        'signal': signal,
                        'current_price': current_price,
                        'weight': self._get_timeframe_weight(tf_name)
                    }

            except Exception as e:
                print(f"Error analyzing {tf_name}: {e}")
                continue

        self.analyses = results
        return results

    def _get_timeframe_weight(self, timeframe: str) -> float:
        """Get weight for timeframe in signal aggregation"""
        weights = {
            '1h': 0.2,   # Short-term, less weight
            '4h': 0.5,   # Medium-term, main timeframe
            '1d': 0.3    # Long-term, important for trend
        }
        return weights.get(timeframe, 0.0)

    def get_aggregated_signal(self) -> Dict[str, Any]:
        """Aggregate signals from all timeframes with confirmation requirement"""
        if not self.analyses:
            return {'signal': 'HOLD', 'confidence': 0.0, 'reason': 'No data available'}

        total_weight = 0
        signal_scores = {'LONG': 0, 'SHORT': 0, 'HOLD': 0, 'EXIT': 0}
        reasons = []
        confidence_sum = 0

        # Count signals per timeframe
        timeframe_signals = {}
        for tf, data in self.analyses.items():
            weight = data['weight']
            signal = data['signal']['signal']
            confidence = data['signal']['confidence']

            signal_scores[signal] += weight
            confidence_sum += confidence * weight
            total_weight += weight

            timeframe_signals[tf] = {'signal': signal, 'confidence': confidence, 'weight': weight}

            if confidence > 0.5:  # Only include strong signals
                reasons.append(f"{tf}: {data['signal']['reason']}")

        # Multi-timeframe confirmation logic
        final_signal = 'HOLD'
        final_confidence = 0.0

        if total_weight > 0:
            confidence_avg = confidence_sum / total_weight

            # Check for multi-timeframe confirmation
            long_timeframes = [tf for tf, data in timeframe_signals.items()
                             if data['signal'] == 'LONG' and data['confidence'] > 0.6]
            short_timeframes = [tf for tf, data in timeframe_signals.items()
                               if data['signal'] == 'SHORT' and data['confidence'] > 0.6]

            # Require at least 2 timeframes agreement for actionable signals
            if len(long_timeframes) >= 2 and signal_scores['LONG'] > signal_scores['SHORT']:
                final_signal = 'LONG'
                # Use weighted confidence from confirming timeframes
                confirming_confidence = sum(timeframe_signals[tf]['confidence'] * timeframe_signals[tf]['weight']
                                          for tf in long_timeframes)
                confirming_weight = sum(timeframe_signals[tf]['weight'] for tf in long_timeframes)
                final_confidence = confirming_confidence / confirming_weight if confirming_weight > 0 else confidence_avg

            elif len(short_timeframes) >= 2 and signal_scores['SHORT'] > signal_scores['LONG']:
                final_signal = 'SHORT'
                confirming_confidence = sum(timeframe_signals[tf]['confidence'] * timeframe_signals[tf]['weight']
                                          for tf in short_timeframes)
                confirming_weight = sum(timeframe_signals[tf]['weight'] for tf in short_timeframes)
                final_confidence = confirming_confidence / confirming_weight if confirming_weight > 0 else confidence_avg

            elif signal_scores['EXIT'] > signal_scores['HOLD']:
                final_signal = 'EXIT'
                final_confidence = confidence_avg * 0.8  # Slightly reduce confidence for exit signals

            else:
                final_signal = 'HOLD'
                final_confidence = confidence_avg * 0.5  # Reduce confidence when no clear consensus

        # Calculate entry price for LONG/SHORT signals
        entry_price = None
        if final_signal in ['LONG', 'SHORT']:
            # Use the current price from the main timeframe (4h)
            if '4h' in self.analyses:
                entry_price = self.analyses['4h']['current_price']

        # Add confirmation info to reasons
        if final_signal in ['LONG', 'SHORT']:
            confirming_tfs = long_timeframes if final_signal == 'LONG' else short_timeframes
            reasons.append(f"Confirmed by {len(confirming_tfs)} timeframes: {', '.join(confirming_tfs)}")

        return {
            'signal': final_signal,
            'confidence': min(final_confidence, 1.0),
            'reason': '; '.join(reasons) if reasons else 'Multi-timeframe analysis',
            'entry_price': entry_price,
            'timeframes': list(self.analyses.keys())
        }