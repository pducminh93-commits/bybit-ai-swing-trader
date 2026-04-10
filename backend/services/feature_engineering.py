import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from .ta_analysis import TechnicalAnalysis

class FeatureEngineer:
    """
    Kết hợp các nguồn dữ liệu (OHLCV, Open Interest, Funding Rate)
    và tính toán các đặc trưng (features) nâng cao phục vụ cho Machine Learning.
    """
    def __init__(self, klines_data: List[List[str]], oi_data: Optional[List[Dict[str, Any]]] = None, fr_data: Optional[List[Dict[str, Any]]] = None):
        # 1. Khởi tạo Klines DataFrame
        self.ta = TechnicalAnalysis(klines_data)
        self.df = self.ta.df.copy() # Inherit OHLCV df
        
        # 2. Xử lý Open Interest Data
        if oi_data and len(oi_data) > 0:
            oi_df = pd.DataFrame(oi_data)
            # Bybit v5 OI returns 'timestamp' string
            oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp'].astype('int64'), unit='ms')
            oi_df['openInterest'] = oi_df['openInterest'].astype(float)
            oi_df.set_index('timestamp', inplace=True)
            # Align with Klines timeframes
            self.df = self.df.join(oi_df['openInterest'], how='left')
            self.df['openInterest'] = self.df['openInterest'].ffill() # Forward fill missing OI
        else:
            self.df['openInterest'] = np.nan

        # 3. Xử lý Funding Rate Data
        if fr_data and len(fr_data) > 0:
            fr_df = pd.DataFrame(fr_data)
            fr_df['fundingRateTimestamp'] = pd.to_datetime(fr_df['fundingRateTimestamp'].astype('int64'), unit='ms')
            fr_df['fundingRate'] = fr_df['fundingRate'].astype(float)
            fr_df.set_index('fundingRateTimestamp', inplace=True)
            # Funding rate often updates every 8h, so we join and forward fill
            self.df = self.df.join(fr_df['fundingRate'], how='left')
            self.df['fundingRate'] = self.df['fundingRate'].ffill()
        else:
            self.df['fundingRate'] = np.nan

    def generate_all_features(self) -> pd.DataFrame:
        """
        Tính toán toàn bộ các features (TA cơ bản + Data Flows nâng cao)
        """
        # 1. Tính toán các chỉ báo TA cơ bản (từ module có sẵn)
        ta_indicators = self.ta.calculate_indicators()
        for key, value in ta_indicators.items():
            # Trong thực tế self.ta.calculate_indicators() trả về giá trị cuối cùng,
            # Nếu muốn tính full array (series) cần sửa lại ta_analysis.py hoặc tính lại ở đây.
            # Tạm thời để demo, tôi sẽ tính trực tiếp một vài cột DataFrame.
            pass
        
        # Để an toàn và đồng bộ, tính trực tiếp trên DataFrame bằng TA-lib
        import talib as ta
        close = self.df['close'].values
        high = self.df['high'].values
        low = self.df['low'].values
        volume = self.df['volume'].values

        # -- Momentum & Trend --
        self.df['rsi_14'] = ta.RSI(close, timeperiod=14)
        self.df['macd'], self.df['macd_signal'], self.df['macd_hist'] = ta.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        self.df['atr_14'] = ta.ATR(high, low, close, timeperiod=14)
        self.df['adx_14'] = ta.ADX(high, low, close, timeperiod=14)
        
        # -- Volatility --
        self.df['bb_upper'], self.df['bb_middle'], self.df['bb_lower'] = ta.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        self.df['volatility_atr_ratio'] = self.df['atr_14'] / self.df['close']

        # -- Volume & Order Flow --
        self.df['obv'] = ta.OBV(close, volume)
        self.df['cmf'] = self._calculate_cmf(high, low, close, volume, 20)
        
        # -- Advanced Derived Features (OI & Funding) --
        # Xử lý an toàn với các dòng bị NaN do Bybit giới hạn API 200 điểm
        self.df['openInterest'] = self.df['openInterest'].bfill().fillna(0)
        self.df['fundingRate'] = self.df['fundingRate'].bfill().fillna(0)
        
        # Tỷ lệ thay đổi OI (Đo lường tiền bơm vào/rút ra)
        self.df['oi_change_1'] = self.df['openInterest'].pct_change(periods=1).fillna(0)
        self.df['oi_change_4'] = self.df['openInterest'].pct_change(periods=4).fillna(0)
        
        # OI * Price Trend (Tâm lý đám đông)
        self.df['price_change_1'] = self.df['close'].pct_change(periods=1).fillna(0)
        self.df['sentiment_score'] = self.df['price_change_1'] * self.df['oi_change_1']
            
        # Funding rate moving average
        self.df['funding_rate_ma3'] = self.df['fundingRate'].rolling(window=3).mean().fillna(0)
        # Cảnh báo Squeeze (Funding âm nặng hoặc dương nặng)
        self.df['is_extreme_funding'] = np.where(self.df['fundingRate'].abs() > 0.001, 1, 0)

        # Drop NaN values for clean ML dataset (chỉ còn rsi_14, macd cần nến mồi)
        self.df.dropna(inplace=True)
        return self.df

    def _calculate_cmf(self, high, low, close, volume, period=20):
        # Tính Chaikin Money Flow (CMF) trực tiếp trên Series
        mf_multiplier = ((close - low) - (high - close)) / (high - low + 0.00001) # Avoid division by zero
        mf_volume = mf_multiplier * volume
        cmf = pd.Series(mf_volume).rolling(window=period).sum() / pd.Series(volume).rolling(window=period).sum()
        return cmf.values

