import math
import numpy as np
from typing import Dict, Any, Optional, List

class RiskManager:
    """
    Lớp "Khiên" (Shield): Tối ưu quy tắc bảo vệ vốn và đi lệnh linh hoạt (Rule-based Dynamic Sizing).
    Kết hợp giữa thuật toán Volatility (ATR) và Bối cảnh thị trường (ADX, Funding Rate, AI Confidence).
    """
    def __init__(self, max_risk_per_trade_pct: float = 0.02, max_portfolio_risk_pct: float = 0.10):
        # Mặc định rủi ro tối đa 2% vốn cho 1 lệnh
        self.max_risk_pct = max_risk_per_trade_pct
        self.max_portfolio_risk = max_portfolio_risk_pct

    def evaluate_trade(self, 
                       capital: float, 
                       current_price: float, 
                       signal: str, 
                       ai_confidence: float, 
                       atr: float, 
                       adx: float, 
                       is_extreme_funding: bool) -> Dict[str, Any]:
        """
        Đánh giá và trả về quyết định cuối cùng: Đi lệnh với khối lượng bao nhiêu, SL/TP ở đâu, hay bỏ qua?
        """
        # Hỗ trợ cả BUY/SELL và LONG/SHORT
        if signal not in ['BUY', 'SELL', 'LONG', 'SHORT']:
            return {"action": "SKIP", "reason": "Signal is not actionable (HOLD)"}

        # 1. BỘ LỌC CỨNG (Hard Filters): Xác suất AI quá thấp thì không vào lệnh
        if ai_confidence < 0.65: # Yêu cầu AI chắc chắn > 65% mới xét tiếp
            return {"action": "SKIP", "reason": f"AI Confidence too low ({ai_confidence*100:.1f}%)"}

        # 2. TÍNH TOÁN DỪNG LỖ (Stop-loss) DỰA VÀO ĐỘ BIẾN ĐỘNG (Volatility)
        # Sử dụng 1.5 lần ATR làm khoảng cách Stop-loss an toàn (tránh nhiễu)
        sl_distance = 1.5 * atr
        if sl_distance == 0 or math.isnan(sl_distance):
            sl_distance = current_price * 0.01  # Backup: 1% giá trị

        # 3. QUẢN LÝ VỐN CƠ BẢN (Position Sizing bằng R-Multiple)
        # Rủi ro bằng tiền: VD Vốn 1000$, risk 2% = 20$
        risk_amount_usd = capital * self.max_risk_pct
        
        # Khối lượng mua = Số tiền chấp nhận mất / Khoảng cách dừng lỗ
        base_size_asset = risk_amount_usd / sl_distance
        base_size_usd = base_size_asset * current_price

        # 4. TÙY CHỈNH THEO BỐI CẢNH - DYNAMIC SIZING (Linh hoạt như 1 trader thật)
        risk_multiplier = 1.0
        reasons_for_penalty = []

        # A. Thị trường Sideway, nhiễu cao (ADX < 20) => Đánh nhỏ lại một nửa
        if adx < 20:
            risk_multiplier *= 0.5
            reasons_for_penalty.append("Choppy Market (ADX < 20)")

        # B. Tín hiệu Squeeze từ Funding Rate (rủi ro quét râu cực lớn) => Đánh nhỏ lại một nửa
        if is_extreme_funding:
            risk_multiplier *= 0.5
            reasons_for_penalty.append("Extreme Funding Rate (High Squeeze Risk)")
            
        # C. AI Confidence siêu cao (> 85%) và có Trend mạnh (ADX > 30) => Tự tin đánh lớn
        if ai_confidence > 0.85 and adx > 30:
            risk_multiplier = 1.2 # Tăng 20% size
            reasons_for_penalty.append("High AI Confidence + Strong Trend (Bonus Size)")

        # Tính toán size cuối cùng
        final_size_usd = base_size_usd * risk_multiplier

        # Đảm bảo lệnh không vượt quá số vốn hiện có (hoặc dùng margin tối đa an toàn)
        # Setup đòn bẩy ngầm: Nếu final_size > capital thì cần cân nhắc limit lại
        final_size_usd = min(final_size_usd, capital * 3) # Ví dụ tối đa x3 đòn bẩy

        # 5. TÍNH ĐIỂM RA LỆNH (SL / TP)
        # Chuẩn hóa signal
        normalized_signal = 'LONG' if signal in ['BUY', 'LONG'] else 'SHORT'
        
        if normalized_signal == 'LONG':
            sl_price = current_price - sl_distance
            tp_price = current_price + (sl_distance * 2)  # Risk/Reward Ratio mặc định 1:2
        else: # SHORT
            sl_price = current_price + sl_distance
            tp_price = current_price - (sl_distance * 2)

        return {
            "action": "EXECUTE",
            "signal": normalized_signal,
            "final_size_usd": round(final_size_usd, 2),
            "leverage_needed": round(final_size_usd / capital, 2) if final_size_usd > capital else 1,
            "entry_price": current_price,
            "stop_loss": round(sl_price, 4),
            "take_profit": round(tp_price, 4),
            "risk_multiplier_applied": risk_multiplier,
            "notes": " | ".join(reasons_for_penalty) if reasons_for_penalty else "Normal Conditions"
        }

    def optimize_portfolio(self, assets: List[str], expected_returns: List[float],
                          covariance_matrix: List[List[float]], risk_free_rate: float = 0.02) -> Dict[str, Any]:
        """
        Modern Portfolio Theory optimization for multi-asset allocation.
        Returns optimal weights for maximum Sharpe ratio.
        """
        try:
            n_assets = len(assets)
            if n_assets != len(expected_returns) or n_assets != len(covariance_matrix):
                return {"error": "Input dimensions mismatch"}

            # Convert to numpy arrays
            mu = np.array(expected_returns)
            cov = np.array(covariance_matrix)

            # Constraints: weights sum to 1, no short selling
            from scipy.optimize import minimize

            def objective(weights):
                portfolio_return = np.dot(weights, mu)
                portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
                sharpe = (portfolio_return - risk_free_rate) / portfolio_volatility
                return -sharpe  # Minimize negative Sharpe

            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # Sum to 1
            ]
            bounds = [(0, 1) for _ in range(n_assets)]  # No short selling

            # Initial guess: equal weight
            init_weights = np.ones(n_assets) / n_assets

            result = minimize(objective, init_weights, method='SLSQP',
                            bounds=bounds, constraints=constraints)

            if result.success:
                optimal_weights = result.x
                portfolio_return = np.dot(optimal_weights, mu)
                portfolio_volatility = np.sqrt(np.dot(optimal_weights.T, np.dot(cov, optimal_weights)))
                sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility

                return {
                    "optimal_weights": dict(zip(assets, optimal_weights)),
                    "expected_return": portfolio_return,
                    "volatility": portfolio_volatility,
                    "sharpe_ratio": sharpe_ratio,
                    "status": "success"
                }
            else:
                return {"error": "Optimization failed", "message": result.message}

        except ImportError:
            return {"error": "scipy not installed for portfolio optimization"}
        except Exception as e:
            return {"error": str(e)}
