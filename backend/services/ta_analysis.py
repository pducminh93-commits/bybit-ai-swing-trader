import pandas as pd
import numpy as np
import talib as ta
import pywt
from typing import Dict, List, Any

class TechnicalAnalysis:
    def __init__(self, klines_data: List[List[str]]):
        """
        Initialize with Bybit klines data
        klines_data: List of [startTime, open, high, low, close, volume, turnover]
        """
        # Convert to DataFrame
        df = pd.DataFrame(klines_data, columns=['startTime', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        df['startTime'] = pd.to_datetime(df['startTime'].astype('int64'), unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
            df[col] = df[col].astype(float)
        self.df = df.set_index('startTime')

    def calculate_indicators(self) -> Dict[str, Any]:
        """Calculate all technical indicators"""
        indicators = {}

        close = self.df['close'].values
        high = self.df['high'].values
        low = self.df['low'].values

        # Moving Averages
        indicators['sma_20'] = ta.SMA(close, timeperiod=20)[-1] if len(close) >= 20 else None
        indicators['sma_50'] = ta.SMA(close, timeperiod=50)[-1] if len(close) >= 50 else None
        indicators['ema_12'] = ta.EMA(close, timeperiod=12)[-1] if len(close) >= 12 else None
        indicators['ema_26'] = ta.EMA(close, timeperiod=26)[-1] if len(close) >= 26 else None

        # RSI
        indicators['rsi'] = ta.RSI(close, timeperiod=14)[-1] if len(close) >= 14 else None

        # MACD
        macd, macdsignal, macdhist = ta.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        indicators['macd'] = macd[-1] if len(macd) > 0 else None
        indicators['macd_signal'] = macdsignal[-1] if len(macdsignal) > 0 else None
        indicators['macd_hist'] = macdhist[-1] if len(macdhist) > 0 else None

        # Bollinger Bands
        upperband, middleband, lowerband = ta.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        indicators['bb_upper'] = upperband[-1] if len(upperband) > 0 else None
        indicators['bb_middle'] = middleband[-1] if len(middleband) > 0 else None
        indicators['bb_lower'] = lowerband[-1] if len(lowerband) > 0 else None

        # Stochastic Oscillator
        slowk, slowd = ta.STOCH(high, low, close, fastk_period=14, slowk_period=3, slowd_period=3)
        indicators['stoch_k'] = slowk[-1] if len(slowk) > 0 else None
        indicators['stoch_d'] = slowd[-1] if len(slowd) > 0 else None

        # ATR (Average True Range)
        indicators['atr'] = ta.ATR(high, low, close, timeperiod=14)[-1] if len(close) >= 14 else None

        # Advanced Indicators

        # ADX (Average Directional Movement Index)
        adx = ta.ADX(high, low, close, timeperiod=14)
        indicators['adx'] = adx[-1] if len(adx) > 0 else None
        indicators['adx_trend'] = 'strong' if indicators['adx'] and indicators['adx'] > 25 else 'weak'

        # Williams %R
        willr = ta.WILLR(high, low, close, timeperiod=14)
        indicators['williams_r'] = willr[-1] if len(willr) > 0 else None

        # OBV (On Balance Volume)
        volume = self.df['volume'].values.astype(float)
        obv = ta.OBV(close, volume)
        indicators['obv'] = obv[-1] if len(obv) > 0 else None

        # Ichimoku Cloud
        tenkan_sen = (ta.MAX(high, 9) + ta.MIN(low, 9)) / 2
        kijun_sen = (ta.MAX(high, 26) + ta.MIN(low, 26)) / 2
        senkou_span_a = (tenkan_sen + kijun_sen) / 2
        senkou_span_b = (ta.MAX(high, 52) + ta.MIN(low, 52)) / 2
        chikou_span = close

        indicators['tenkan_sen'] = tenkan_sen[-1] if len(tenkan_sen) > 0 else None
        indicators['kijun_sen'] = kijun_sen[-1] if len(kijun_sen) > 0 else None
        indicators['senkou_span_a'] = senkou_span_a[-1] if len(senkou_span_a) > 0 else None
        indicators['senkou_span_b'] = senkou_span_b[-1] if len(senkou_span_b) > 0 else None
        indicators['chikou_span'] = chikou_span[-1] if len(chikou_span) > 0 else None

        # Commodity Channel Index (CCI)
        cci = ta.CCI(high, low, close, timeperiod=20)
        indicators['cci'] = cci[-1] if len(cci) > 0 else None

        # Money Flow Index (MFI)
        mfi = ta.MFI(high, low, close, volume, timeperiod=14)
        indicators['mfi'] = mfi[-1] if len(mfi) > 0 else None

        # Chaikin Money Flow (CMF)
        cmf_period = 20
        if len(close) >= cmf_period:
            # Simplified CMF calculation
            mf_multiplier = ((close - low) - (high - close)) / (high - low)
            mf_volume = mf_multiplier * volume
            cmf = ta.SMA(mf_volume, cmf_period) / ta.SMA(volume, cmf_period)
            indicators['cmf'] = cmf[-1] if len(cmf) > 0 else None

        # Wavelet Transform features
        wavelet_features = self._calculate_wavelet_features(close)
        indicators.update(wavelet_features)

        return indicators

    def _calculate_wavelet_features(self, close: np.ndarray) -> Dict[str, Any]:
        """Calculate wavelet transform features for trend analysis"""
        features = {}

        if len(close) < 16:  # Minimum length for wavelet
            return features

        try:
            # Use Discrete Wavelet Transform with db4 wavelet
            coeffs = pywt.dwt(close, 'db4')
            cA, cD = coeffs  # Approximation and detail coefficients

            # Features from approximation coefficients (trend)
            features['wavelet_approx_mean'] = np.mean(cA[-10:]) if len(cA) >= 10 else None
            features['wavelet_approx_std'] = np.std(cA[-10:]) if len(cA) >= 10 else None

            # Features from detail coefficients (noise/details)
            features['wavelet_detail_energy'] = np.sum(cD**2) / len(cD) if len(cD) > 0 else None
            features['wavelet_detail_std'] = np.std(cD) if len(cD) > 0 else None

            # Trend strength indicator
            if len(cA) >= 2 and len(cD) >= 2:
                trend_ratio = np.abs(np.mean(cA[-5:]) - np.mean(cA[-10:-5])) / (np.std(cD[-5:]) + 1e-8)
                features['wavelet_trend_strength'] = trend_ratio

        except Exception as e:
            # Wavelet calculation failed
            features['wavelet_error'] = str(e)

        return features

    def get_latest_price(self) -> float:
        """Get latest close price"""
        return self.df['close'].iloc[-1]

    def get_price_change(self, periods: int = 1) -> float:
        """Get price change over last n periods"""
        if len(self.df) < periods + 1:
            return 0.0
        return (self.df['close'].iloc[-1] - self.df['close'].iloc[-periods-1]) / self.df['close'].iloc[-periods-1] * 100

    def get_fibonacci_levels(self, lookback: int = 50) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels"""
        if len(self.df) < lookback:
            return {}

        recent_data = self.df.tail(lookback)
        high = recent_data['high'].max()
        low = recent_data['low'].min()
        diff = high - low

        fib_levels = {
            'fib_0.236': high - diff * 0.236,
            'fib_0.382': high - diff * 0.382,
            'fib_0.5': high - diff * 0.5,
            'fib_0.618': high - diff * 0.618,
            'fib_0.786': high - diff * 0.786,
            'fib_high': high,
            'fib_low': low
        }

        return fib_levels

    def detect_candlestick_patterns(self) -> Dict[str, bool]:
        """Detect basic candlestick patterns"""
        if len(self.df) < 2:
            return {}

        patterns = {}

        # Current and previous candles
        current = self.df.iloc[-1]
        previous = self.df.iloc[-2]

        open_c, high_c, low_c, close_c = current['open'], current['high'], current['low'], current['close']
        open_p, high_p, low_p, close_p = previous['open'], previous['high'], previous['low'], previous['close']

        # Bullish patterns
        # Hammer: small body, long lower wick, little/no upper wick
        body_size = abs(close_c - open_c)
        total_range = high_c - low_c
        lower_wick = min(open_c, close_c) - low_c
        upper_wick = high_c - max(open_c, close_c)

        if body_size > 0 and total_range > 0:
            patterns['hammer'] = lower_wick > body_size * 2 and upper_wick < body_size * 0.3
            patterns['shooting_star'] = upper_wick > body_size * 2 and lower_wick < body_size * 0.3
            patterns['doji'] = body_size / total_range < 0.1

        # Engulfing patterns
        if close_p > open_p:  # Previous bullish
            patterns['bearish_engulfing'] = close_c < open_c and open_c > close_p and close_c < open_p
        elif close_p < open_p:  # Previous bearish
            patterns['bullish_engulfing'] = close_c > open_c and close_c > open_p and open_c < close_p

        # Marubozu
        patterns['bullish_marubozu'] = close_c > open_c and lower_wick < body_size * 0.1 and upper_wick < body_size * 0.1
        patterns['bearish_marubozu'] = close_c < open_c and lower_wick < body_size * 0.1 and upper_wick < body_size * 0.1

        return patterns