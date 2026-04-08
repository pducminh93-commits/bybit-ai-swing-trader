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
                    signal = ai_gen.generate_signal(indicators, current_price)

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
        """Aggregate signals from all timeframes"""
        if not self.analyses:
            return {'signal': 'HOLD', 'confidence': 0.0, 'reason': 'No data available'}

        total_weight = 0
        signal_scores = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        reasons = []
        confidence_sum = 0

        for tf, data in self.analyses.items():
            weight = data['weight']
            signal = data['signal']['signal']
            confidence = data['signal']['confidence']

            signal_scores[signal] += weight
            confidence_sum += confidence * weight
            total_weight += weight

            if confidence > 0.5:  # Only include strong signals
                reasons.append(f"{tf}: {data['signal']['reason']}")

        # Determine aggregated signal
        if total_weight > 0:
            confidence_avg = confidence_sum / total_weight

            if signal_scores['BUY'] > signal_scores['SELL'] and signal_scores['BUY'] > signal_scores['HOLD']:
                final_signal = 'BUY'
            elif signal_scores['SELL'] > signal_scores['BUY'] and signal_scores['SELL'] > signal_scores['HOLD']:
                final_signal = 'SELL'
            else:
                final_signal = 'HOLD'

            # Adjust confidence based on agreement
            max_score = max(signal_scores.values())
            agreement_ratio = max_score / total_weight
            final_confidence = confidence_avg * agreement_ratio

        else:
            final_signal = 'HOLD'
            final_confidence = 0.0

        return {
            'signal': final_signal,
            'confidence': min(final_confidence, 1.0),
            'reason': '; '.join(reasons) if reasons else 'Multi-timeframe analysis',
            'timeframes': list(self.analyses.keys())
        }