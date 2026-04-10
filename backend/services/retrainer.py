import os
import time
import logging
from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
import numpy as np

from .bybit_service import BybitService
from .feature_engineering import FeatureEngineer
from .ml_model import MLSignalPredictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WalkForwardTrainer")

class WalkForwardTrainer:
    """
    Cơ chế tiến hóa (Continual Learning): 
    Tự động kéo dữ liệu mới nhất, tính toán đặc trưng và huấn luyện lại (Retrain) mô hình
    theo phương pháp cửa sổ trượt (Sliding Window / Walk-forward).
    Hỗ trợ Global Model (Huấn luyện đa cặp tiền).
    """
    def __init__(self, symbols: List[str] = None, timeframe: str = "240"):
        # Danh sách các coin đại diện cho thị trường để tạo Siêu tập dữ liệu
        if symbols is None:
            self.symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT"]
        else:
            self.symbols = symbols
            
        self.timeframe = timeframe
        # Thay đổi logic bên dưới để tự dùng VotingClassifier thay vì phụ thuộc MLSignalPredictor cũ
        
    def fetch_and_prepare_data(self, symbol: str) -> pd.DataFrame:
        """Kéo dữ liệu mới nhất và chạy Feature Engineering cho một coin"""
        logger.info(f"Đang tải dữ liệu mới nhất cho {symbol}...")
        
        # 1. Kéo dữ liệu
        klines_resp = BybitService.fetch_klines(symbol, interval=self.timeframe, limit=1000)
        oi_resp = BybitService.fetch_open_interest(symbol, intervalTime="4h", limit=500)
        fr_resp = BybitService.fetch_funding_rate_history(symbol, limit=500)
        
        # 2. Xử lý API response
        klines = klines_resp.get('result', {}).get('list', [])
        # Đảo ngược vì Bybit trả về mới nhất trước
        klines = klines[::-1] 
        
        oi_data = oi_resp.get('result', {}).get('list', [])
        fr_data = fr_resp.get('result', {}).get('list', [])
        
        # 3. Tính toán Features
        engineer = FeatureEngineer(klines, oi_data, fr_data)
        df_features = engineer.generate_all_features()
        
        return df_features

    def create_labels(self, df: pd.DataFrame, lookahead: int = 5) -> pd.DataFrame:
        """Tạo nhãn (Targets) dựa trên tương lai để ML học"""
        # Tạo cột giá max/min trong N cây nến tiếp theo
        df['future_max'] = df['close'].shift(-lookahead).rolling(lookahead).max()
        df['future_min'] = df['close'].shift(-lookahead).rolling(lookahead).min()
        
        # Tính % thay đổi
        df['upside'] = (df['future_max'] - df['close']) / df['close'] * 100
        df['downside'] = (df['close'] - df['future_min']) / df['close'] * 100
        
        # Gán nhãn: 2 (BUY) nếu upside > 2% & upside > downside, 0 (SELL) nếu downside mạnh hơn, 1 (HOLD)
        conditions = [
            (df['upside'] > 2) & (df['upside'] > df['downside']),
            (df['downside'] > 2) & (df['downside'] > df['upside'])
        ]
        choices = [2, 0] # BUY, SELL
        df['target'] = np.select(conditions, choices, default=1) # Mặc định là HOLD
        
        # Bỏ các dòng NaN (do shift tạo ra ở cuối)
        df.dropna(inplace=True)
        return df

    def retrain_universal_model(self):
        """Thực thi toàn bộ pipeline huấn luyện Universal Model (Global Model)"""
        logger.info(f"Bắt đầu chu trình Walk-forward Universal Retraining...")
        
        all_dfs = []
        
        # Vòng lặp kéo dữ liệu tất cả các coin
        for sym in self.symbols:
            try:
                df = self.fetch_and_prepare_data(sym)
                df = self.create_labels(df)
                if len(df) >= 100: # Hạ ngưỡng xuống vì API Bybit giới hạn lịch sử OI/FR max 200
                    # Giữ lại 800 nến gần nhất (hoặc ít hơn nếu không đủ)
                    recent_df = df.tail(800).copy()
                    recent_df['symbol_label'] = sym # Thêm nhãn để debug
                    all_dfs.append(recent_df)
                else:
                    logger.warning(f"Không đủ dữ liệu cho {sym} (Chỉ có {len(df)} dòng sau khi merge)")
            except Exception as e:
                logger.error(f"Lỗi khi tải dữ liệu cho {sym}: {e}")
                
        if not all_dfs:
            logger.error("Thất bại: Không gom được dữ liệu nào!")
            return False
            
        # Trộn chung thành Siêu tập dữ liệu (Mega Dataset)
        mega_df = pd.concat(all_dfs, ignore_index=True)
        logger.info(f"Đã tạo Siêu tập dữ liệu với {len(mega_df)} mẫu từ {len(all_dfs)} coins.")
        
        # Xáo trộn dữ liệu (Shuffle) để model không bị thiên vị học theo thứ tự coin
        mega_df = mega_df.sample(frac=1, random_state=42).reset_index(drop=True)
        
        # Tách Features (X) và Target (y)
        exclude_cols = ['target', 'symbol_label', 'future_max', 'future_min', 'upside', 'downside', 'startTime', 'open', 'high', 'low', 'close', 'volume', 'turnover']
        feature_cols = [col for col in mega_df.columns if col not in exclude_cols]
        
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import train_test_split
        import joblib
        
        X = mega_df[feature_cols].values
        y = mega_df['target'].values
        
        # Chia train/test (80/20)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Cập nhật Scaler
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Khởi tạo mô hình Ensemble (Soft Voting Mix)
        logger.info("Đang fitting mô hình Universal Ensemble (RF + GB) với Siêu tập dữ liệu...")
        rf_model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10, n_jobs=-1)
        gb_model = GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=5)
        
        universal_model = VotingClassifier(
            estimators=[('rf', rf_model), ('gb', gb_model)],
            voting='soft'
        )
        
        # Huấn luyện
        universal_model.fit(X_train_scaled, y_train)
        
        # Đánh giá
        score = universal_model.score(X_test_scaled, y_test)
        logger.info(f"Độ chính xác (Accuracy) trên Siêu tập dữ liệu (Test set): {score*100:.2f}%")
        
        # Lưu lại Version Universal mới
        os.makedirs('models', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Lưu đè model Universal chính
        joblib.dump(universal_model, f'models/universal_ensemble_model.pkl')
        joblib.dump(scaler, f'models/universal_ensemble_scaler.pkl')
        
        # Lưu backup version
        os.makedirs('models/backups', exist_ok=True)
        joblib.dump(universal_model, f'models/backups/universal_ensemble_{timestamp}_model.pkl')
        
        logger.info(f"Đã lưu thành công mô hình Universal mới lúc {timestamp}")
        
        # Trích xuất Feature Importance để hiển thị cho UI
        feature_importance = {}
        try:
            rf_imp = universal_model.named_estimators_['rf'].feature_importances_
            gb_imp = universal_model.named_estimators_['gb'].feature_importances_
            avg_imp = (rf_imp + gb_imp) / 2
            feature_importance = dict(zip(feature_cols, avg_imp))
        except Exception as e:
            logger.warning(f"Không thể trích xuất feature_importance: {e}")
            
        return {
            "status": "success",
            "accuracy": float(score),
            "feature_importance": feature_importance
        }

if __name__ == "__main__":
    trainer = WalkForwardTrainer()
    trainer.retrain_universal_model()
