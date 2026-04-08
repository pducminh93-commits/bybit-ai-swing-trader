import numpy as np
from typing import Dict, Any, Optional
from services.ta_analysis import TechnicalAnalysis

class AISignalGenerator:
    def __init__(self):
        # Thresholds for signals
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.macd_bullish_threshold = 0
        self.bb_deviation_threshold = 0.02  # 2% from bands
        self.cci_overbought = 100
        self.cci_oversold = -100
        self.williams_overbought = -20
        self.williams_oversold = -80
        self.mfi_overbought = 80
        self.mfi_oversold = 20

    def generate_signal(self, indicators: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        Generate trading signal based on technical indicators
        Returns: {'signal': 'BUY'/'SELL'/'HOLD', 'confidence': float, 'reason': str, 'tp': float, 'sl': float}
        """
        signal = 'HOLD'
        confidence = 0.0
        reasons = []

        # RSI Analysis
        if indicators.get('rsi'):
            rsi = indicators['rsi']
            if rsi < self.rsi_oversold:
                signal = 'BUY'
                confidence += 0.3
                reasons.append(f"RSI oversold ({rsi:.2f})")
            elif rsi > self.rsi_overbought:
                signal = 'SELL'
                confidence += 0.3
                reasons.append(f"RSI overbought ({rsi:.2f})")

        # MACD Analysis
        if indicators.get('macd') is not None and indicators.get('macd_signal') is not None:
            macd = indicators['macd']
            macd_signal = indicators['macd_signal']
            if macd > macd_signal and macd > self.macd_bullish_threshold:
                if signal == 'HOLD':
                    signal = 'BUY'
                confidence += 0.2
                reasons.append("MACD bullish crossover")
            elif macd < macd_signal:
                if signal == 'HOLD':
                    signal = 'SELL'
                confidence += 0.2
                reasons.append("MACD bearish crossover")

        # Bollinger Bands Analysis
        if indicators.get('bb_upper') and indicators.get('bb_lower'):
            bb_upper = indicators['bb_upper']
            bb_middle = indicators['bb_middle']
            bb_lower = indicators['bb_lower']

            price_to_upper = abs(current_price - bb_upper) / bb_upper
            price_to_lower = abs(current_price - bb_lower) / bb_lower

            if current_price < bb_lower * (1 - self.bb_deviation_threshold):
                if signal == 'HOLD':
                    signal = 'BUY'
                confidence += 0.25
                reasons.append("Price near lower Bollinger Band")
            elif current_price > bb_upper * (1 + self.bb_deviation_threshold):
                if signal == 'HOLD':
                    signal = 'SELL'
                confidence += 0.25
                reasons.append("Price near upper Bollinger Band")

        # Moving Averages Analysis
        if indicators.get('sma_20') and indicators.get('sma_50'):
            sma20 = indicators['sma_20']
            sma50 = indicators['sma_50']
            if current_price > sma20 > sma50:
                if signal == 'HOLD':
                    signal = 'BUY'
                confidence += 0.15
                reasons.append("Price above SMAs with golden cross")
            elif current_price < sma20 < sma50:
                if signal == 'HOLD':
                    signal = 'SELL'
                confidence += 0.15
                reasons.append("Price below SMAs with death cross")

        # Advanced Indicators Analysis

        # ADX for trend strength
        if indicators.get('adx') and indicators.get('adx_trend'):
            adx = indicators['adx']
            if adx > 25:  # Strong trend
                confidence += 0.1
                reasons.append(f"Strong trend (ADX: {adx:.1f})")
            elif adx < 20:  # Weak trend, possible reversal
                confidence += 0.05
                reasons.append("Weak trend, watch for reversal")

        # Williams %R
        if indicators.get('williams_r'):
            willr = indicators['williams_r']
            if willr < self.williams_oversold:
                if signal == 'HOLD':
                    signal = 'BUY'
                confidence += 0.2
                reasons.append(f"Williams %R oversold ({willr:.1f})")
            elif willr > self.williams_overbought:
                if signal == 'HOLD':
                    signal = 'SELL'
                confidence += 0.2
                reasons.append(f"Williams %R overbought ({willr:.1f})")

        # CCI (Commodity Channel Index)
        if indicators.get('cci'):
            cci = indicators['cci']
            if cci < self.cci_oversold:
                if signal == 'HOLD':
                    signal = 'BUY'
                confidence += 0.18
                reasons.append(f"CCI oversold ({cci:.1f})")
            elif cci > self.cci_overbought:
                if signal == 'HOLD':
                    signal = 'SELL'
                confidence += 0.18
                reasons.append(f"CCI overbought ({cci:.1f})")

        # MFI (Money Flow Index)
        if indicators.get('mfi'):
            mfi = indicators['mfi']
            if mfi < self.mfi_oversold:
                if signal == 'HOLD':
                    signal = 'BUY'
                confidence += 0.15
                reasons.append(f"MFI oversold ({mfi:.1f})")
            elif mfi > self.mfi_overbought:
                if signal == 'HOLD':
                    signal = 'SELL'
                confidence += 0.15
                reasons.append(f"MFI overbought ({mfi:.1f})")

        # Ichimoku Cloud Analysis
        if (indicators.get('tenkan_sen') and indicators.get('kijun_sen') and
            indicators.get('senkou_span_a') and indicators.get('senkou_span_b')):
            tenkan = indicators['tenkan_sen']
            kijun = indicators['kijun_sen']
            senkou_a = indicators['senkou_span_a']
            senkou_b = indicators['senkou_span_b']

            # Tenkan/Kijun cross
            if tenkan > kijun and signal == 'HOLD':
                signal = 'BUY'
                confidence += 0.12
                reasons.append("Ichimoku Tenkan above Kijun")
            elif tenkan < kijun and signal == 'HOLD':
                signal = 'SELL'
                confidence += 0.12
                reasons.append("Ichimoku Tenkan below Kijun")

            # Price vs Cloud
            cloud_top = max(senkou_a, senkou_b)
            cloud_bottom = min(senkou_a, senkou_b)
            if current_price > cloud_top:
                confidence += 0.1
                reasons.append("Price above Ichimoku cloud")
            elif current_price < cloud_bottom:
                confidence += 0.08
                reasons.append("Price below Ichimoku cloud")

        # Calculate TP and SL
        tp, sl = self.calculate_tp_sl(signal, current_price, indicators)

        return {
            'signal': signal,
            'confidence': min(confidence, 1.0),
            'reason': '; '.join(reasons),
            'take_profit': tp,
            'stop_loss': sl
        }

    def calculate_tp_sl(self, signal: str, current_price: float, indicators: Dict[str, Any]) -> tuple[float, float]:
        """Calculate take profit and stop loss levels"""
        if signal == 'HOLD':
            return 0.0, 0.0

        # Use ATR for dynamic SL/TP if available
        atr = indicators.get('atr', current_price * 0.02)  # Default 2% if no ATR

        risk_multiplier = 1.5
        reward_multiplier = 3.0

        if signal == 'BUY':
            sl = current_price - (atr * risk_multiplier)
            tp = current_price + (atr * reward_multiplier)
        else:  # SELL
            sl = current_price + (atr * risk_multiplier)
            tp = current_price - (atr * reward_multiplier)

        return round(tp, 4), round(sl, 4)