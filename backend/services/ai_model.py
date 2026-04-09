import numpy as np
from typing import Dict, Any, Optional
from services.ta_analysis import TechnicalAnalysis

class AISignalGenerator:
    def __init__(self):
        # Thresholds for signals with hysteresis
        # Entry thresholds (stricter)
        self.rsi_overbought_entry = 75
        self.rsi_oversold_entry = 25
        # Exit thresholds (looser)
        self.rsi_overbought_exit = 65
        self.rsi_oversold_exit = 35

        self.macd_bullish_threshold = 0
        self.bb_deviation_threshold = 0.02  # 2% from bands

        # CCI with hysteresis
        self.cci_overbought_entry = 120
        self.cci_oversold_entry = -120
        self.cci_overbought_exit = 80
        self.cci_oversold_exit = -80

        # Williams %R with hysteresis
        self.williams_overbought_entry = -15
        self.williams_oversold_entry = -85
        self.williams_overbought_exit = -30
        self.williams_oversold_exit = -70

        # MFI with hysteresis
        self.mfi_overbought_entry = 85
        self.mfi_oversold_entry = 15
        self.mfi_overbought_exit = 75
        self.mfi_oversold_exit = 25

        # Signal stability settings
        self.min_confidence_change = 0.15  # Minimum confidence change to update signal
        self.min_time_between_changes = 300  # 5 minutes minimum between signal changes

        # Signal history tracking
        self.last_signals = {}  # symbol -> {'signal': str, 'confidence': float, 'timestamp': int}
        self.current_positions = {}  # symbol -> current position ('LONG', 'SHORT', or None)

    def generate_signal(self, indicators: Dict[str, Any], current_price: float, symbol: str = "UNKNOWN") -> Dict[str, Any]:
        """
        Generate trading signal based on technical indicators with hysteresis
        Returns: {'signal': 'LONG'/'SHORT'/'HOLD'/'EXIT', 'confidence': float, 'reason': str, 'tp': float, 'sl': float, 'entry_price': float}
        """
        import time
        current_time = int(time.time())

        # Get current position for this symbol
        current_position = self.current_positions.get(symbol)

        signal = 'HOLD'
        confidence = 0.0
        reasons = []
        bullish_signals = 0
        bearish_signals = 0

        # RSI Analysis with hysteresis
        if indicators.get('rsi'):
            rsi = indicators['rsi']

            # Use different thresholds based on current position
            if current_position == 'LONG':
                # Already long, use exit threshold
                if rsi > self.rsi_overbought_exit:
                    signal = 'SHORT'
                    confidence += 0.3
                    reasons.append(f"RSI overbought exit ({rsi:.2f} > {self.rsi_overbought_exit})")
                    bearish_signals += 1
                elif rsi < self.rsi_oversold_exit:
                    # Stay long
                    bullish_signals += 1
            elif current_position == 'SHORT':
                # Already short, use exit threshold
                if rsi < self.rsi_oversold_exit:
                    signal = 'LONG'
                    confidence += 0.3
                    reasons.append(f"RSI oversold exit ({rsi:.2f} < {self.rsi_oversold_exit})")
                    bullish_signals += 1
                elif rsi > self.rsi_overbought_exit:
                    # Stay short
                    bearish_signals += 1
            else:
                # No position, use entry thresholds
                if rsi < self.rsi_oversold_entry:
                    signal = 'LONG'
                    confidence += 0.3
                    reasons.append(f"RSI oversold entry ({rsi:.2f} < {self.rsi_oversold_entry})")
                    bullish_signals += 1
                elif rsi > self.rsi_overbought_entry:
                    signal = 'SHORT'
                    confidence += 0.3
                    reasons.append(f"RSI overbought entry ({rsi:.2f} > {self.rsi_overbought_entry})")
                    bearish_signals += 1

        # MACD Analysis (no hysteresis needed for MACD crossovers)
        if indicators.get('macd') is not None and indicators.get('macd_signal') is not None:
            macd = indicators['macd']
            macd_signal = indicators['macd_signal']
            if macd > macd_signal and macd > self.macd_bullish_threshold:
                if signal == 'HOLD':
                    signal = 'LONG'
                confidence += 0.2
                reasons.append("MACD bullish crossover")
                bullish_signals += 1
            elif macd < macd_signal:
                if signal == 'HOLD':
                    signal = 'SHORT'
                confidence += 0.2
                reasons.append("MACD bearish crossover")
                bearish_signals += 1

        # Bollinger Bands Analysis
        if indicators.get('bb_upper') and indicators.get('bb_lower'):
            bb_upper = indicators['bb_upper']
            bb_middle = indicators['bb_middle']
            bb_lower = indicators['bb_lower']

            price_to_upper = abs(current_price - bb_upper) / bb_upper
            price_to_lower = abs(current_price - bb_lower) / bb_lower

            if current_price < bb_lower * (1 - self.bb_deviation_threshold):
                if signal == 'HOLD':
                    signal = 'LONG'
                confidence += 0.25
                reasons.append("Price near lower Bollinger Band")
                bullish_signals += 1
            elif current_price > bb_upper * (1 + self.bb_deviation_threshold):
                if signal == 'HOLD':
                    signal = 'SHORT'
                confidence += 0.25
                reasons.append("Price near upper Bollinger Band")
                bearish_signals += 1

        # Moving Averages Analysis
        if indicators.get('sma_20') and indicators.get('sma_50'):
            sma20 = indicators['sma_20']
            sma50 = indicators['sma_50']
            if current_price > sma20 > sma50:
                if signal == 'HOLD':
                    signal = 'LONG'
                confidence += 0.15
                reasons.append("Price above SMAs with golden cross")
                bullish_signals += 1
            elif current_price < sma20 < sma50:
                if signal == 'HOLD':
                    signal = 'SHORT'
                confidence += 0.15
                reasons.append("Price below SMAs with death cross")
                bearish_signals += 1

        # Williams %R with hysteresis
        if indicators.get('williams_r'):
            willr = indicators['williams_r']

            if current_position == 'LONG':
                if willr > self.williams_overbought_exit:
                    if signal == 'HOLD':
                        signal = 'SHORT'
                    confidence += 0.2
                    reasons.append(f"Williams %R overbought exit ({willr:.1f} > {self.williams_overbought_exit})")
                    bearish_signals += 1
            elif current_position == 'SHORT':
                if willr < self.williams_oversold_exit:
                    if signal == 'HOLD':
                        signal = 'LONG'
                    confidence += 0.2
                    reasons.append(f"Williams %R oversold exit ({willr:.1f} < {self.williams_oversold_exit})")
                    bullish_signals += 1
            else:
                if willr < self.williams_oversold_entry:
                    if signal == 'HOLD':
                        signal = 'LONG'
                    confidence += 0.2
                    reasons.append(f"Williams %R oversold entry ({willr:.1f} < {self.williams_oversold_entry})")
                    bullish_signals += 1
                elif willr > self.williams_overbought_entry:
                    if signal == 'HOLD':
                        signal = 'SHORT'
                    confidence += 0.2
                    reasons.append(f"Williams %R overbought entry ({willr:.1f} > {self.williams_overbought_entry})")
                    bearish_signals += 1

        # CCI (Commodity Channel Index) with hysteresis
        if indicators.get('cci'):
            cci = indicators['cci']

            if current_position == 'LONG':
                if cci > self.cci_overbought_exit:
                    if signal == 'HOLD':
                        signal = 'SHORT'
                    confidence += 0.18
                    reasons.append(f"CCI overbought exit ({cci:.1f} > {self.cci_overbought_exit})")
                    bearish_signals += 1
            elif current_position == 'SHORT':
                if cci < self.cci_oversold_exit:
                    if signal == 'HOLD':
                        signal = 'LONG'
                    confidence += 0.18
                    reasons.append(f"CCI oversold exit ({cci:.1f} < {self.cci_oversold_exit})")
                    bullish_signals += 1
            else:
                if cci < self.cci_oversold_entry:
                    if signal == 'HOLD':
                        signal = 'LONG'
                    confidence += 0.18
                    reasons.append(f"CCI oversold entry ({cci:.1f} < {self.cci_oversold_entry})")
                    bullish_signals += 1
                elif cci > self.cci_overbought_entry:
                    if signal == 'HOLD':
                        signal = 'SHORT'
                    confidence += 0.18
                    reasons.append(f"CCI overbought entry ({cci:.1f} > {self.cci_overbought_entry})")
                    bearish_signals += 1

        # MFI (Money Flow Index) with hysteresis
        if indicators.get('mfi'):
            mfi = indicators['mfi']

            if current_position == 'LONG':
                if mfi > self.mfi_overbought_exit:
                    if signal == 'HOLD':
                        signal = 'SHORT'
                    confidence += 0.15
                    reasons.append(f"MFI overbought exit ({mfi:.1f} > {self.mfi_overbought_exit})")
                    bearish_signals += 1
            elif current_position == 'SHORT':
                if mfi < self.mfi_oversold_exit:
                    if signal == 'HOLD':
                        signal = 'LONG'
                    confidence += 0.15
                    reasons.append(f"MFI oversold exit ({mfi:.1f} < {self.mfi_oversold_exit})")
                    bullish_signals += 1
            else:
                if mfi < self.mfi_oversold_entry:
                    if signal == 'HOLD':
                        signal = 'LONG'
                    confidence += 0.15
                    reasons.append(f"MFI oversold entry ({mfi:.1f} < {self.mfi_oversold_entry})")
                    bullish_signals += 1
                elif mfi > self.mfi_overbought_entry:
                    if signal == 'HOLD':
                        signal = 'SHORT'
                    confidence += 0.15
                    reasons.append(f"MFI overbought entry ({mfi:.1f} > {self.mfi_overbought_entry})")
                    bearish_signals += 1

        # Ichimoku Cloud Analysis
        if (indicators.get('tenkan_sen') and indicators.get('kijun_sen') and
            indicators.get('senkou_span_a') and indicators.get('senkou_span_b')):
            tenkan = indicators['tenkan_sen']
            kijun = indicators['kijun_sen']
            senkou_a = indicators['senkou_span_a']
            senkou_b = indicators['senkou_span_b']

            # Tenkan/Kijun cross
            if tenkan > kijun and signal == 'HOLD':
                signal = 'LONG'
                confidence += 0.12
                reasons.append("Ichimoku Tenkan above Kijun")
                bullish_signals += 1
            elif tenkan < kijun and signal == 'HOLD':
                signal = 'SHORT'
                confidence += 0.12
                reasons.append("Ichimoku Tenkan below Kijun")
                bearish_signals += 1

            # Price vs Cloud
            cloud_top = max(senkou_a, senkou_b)
            cloud_bottom = min(senkou_a, senkou_b)
            if current_price > cloud_top:
                confidence += 0.1
                reasons.append("Price above Ichimoku cloud")
            elif current_price < cloud_bottom:
                confidence += 0.08
                reasons.append("Price below Ichimoku cloud")

        # Apply signal stability filters
        last_signal_data = self.last_signals.get(symbol, {'signal': 'HOLD', 'confidence': 0.0, 'timestamp': 0})
        time_since_last_change = current_time - last_signal_data['timestamp']

        # Check if signal should change
        should_change_signal = False

        if signal in ['LONG', 'SHORT']:
            # For actionable signals, require minimum confidence and stability
            if confidence > 0.5 and (bullish_signals >= 2 or bearish_signals >= 2):
                # Check if confidence changed significantly or enough time has passed
                confidence_change = abs(confidence - last_signal_data['confidence'])
                if confidence_change > self.min_confidence_change or time_since_last_change > self.min_time_between_changes:
                    should_change_signal = True
                    entry_price = current_price
                    reasons.append(f"Stable entry signal ({max(bullish_signals, bearish_signals)} indicators aligned)")
                else:
                    # Keep previous signal
                    signal = last_signal_data['signal']
                    confidence = last_signal_data['confidence']
                    reasons.append(f"Signal stable, keeping {signal}")
            else:
                signal = 'HOLD'
        elif confidence < 0.3 or (bullish_signals > 0 and bearish_signals > 0):
            if last_signal_data['signal'] in ['LONG', 'SHORT']:
                signal = 'EXIT'
                reasons.append("Weak/conflicting signals, suggest exit")
            else:
                signal = 'HOLD'

        # Update position tracking
        if signal in ['LONG', 'SHORT']:
            self.current_positions[symbol] = signal
        elif signal == 'EXIT':
            self.current_positions[symbol] = None

        # Update signal history
        if should_change_signal or signal != last_signal_data['signal']:
            self.last_signals[symbol] = {
                'signal': signal,
                'confidence': confidence,
                'timestamp': current_time
            }

        # Calculate TP and SL
        tp, sl = self.calculate_tp_sl(signal, current_price, indicators)

        return {
            'signal': signal,
            'confidence': min(confidence, 1.0),
            'reason': '; '.join(reasons),
            'take_profit': tp,
            'stop_loss': sl,
            'entry_price': entry_price
        }

    def calculate_tp_sl(self, signal: str, current_price: float, indicators: Dict[str, Any]) -> tuple[float, float]:
        """Calculate take profit and stop loss levels"""
        if signal in ['HOLD', 'EXIT']:
            return 0.0, 0.0

        # Use ATR for dynamic SL/TP if available
        atr = indicators.get('atr', current_price * 0.02)  # Default 2% if no ATR

        risk_multiplier = 1.5
        reward_multiplier = 3.0

        if signal == 'LONG':
            sl = current_price - (atr * risk_multiplier)
            tp = current_price + (atr * reward_multiplier)
        elif signal == 'SHORT':
            sl = current_price + (atr * risk_multiplier)
            tp = current_price - (atr * reward_multiplier)
        else:
            return 0.0, 0.0

        return round(tp, 4), round(sl, 4)