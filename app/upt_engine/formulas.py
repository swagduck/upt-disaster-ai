# app/upt_engine/formulas.py
from typing import List
from app.schemas.prediction_schema import SensorData

class UPTMath:
    """
    Unified Pulse Theory (UPT) Mathematical Core.
    Chuyển đổi từ tài liệu lý thuyết UPT_NEWLY.pdf và UPT_CompactNuclearReactor.pdf.
    """

    @staticmethod
    def calculate_resonance(sensors: List[SensorData]) -> float:
        """
        Công thức 3: Cộng Hưởng Tập Thể (Resonance)
        R(t) = Sum(E_i(t) * A_i(t))
        
        [cite_start]Nguồn: [cite: 10] "Tổng cộng hưởng của nhóm cá nhân trong hệ thống"
        Ở đây áp dụng cho mạng lưới cảm biến: Tổng (Năng lượng * Bất thường).
        """
        resonance = sum(s.energy_level * s.anomaly_score * s.location_weight for s in sensors)
        # Chuẩn hóa về 0-1 trung bình để dễ đánh giá (tùy chỉnh theo logic thực tế)
        return resonance / len(sensors) if sensors else 0.0

    @staticmethod
    def calculate_collapse_probability(avg_anomaly: float, avg_energy: float, conditions: float) -> float:
        """
        Công thức 2: Sụp Đổ Xác Suất (Collapse Probability)
        P(phi_k) = A(t) * E(t) * C(t)
        
        [cite_start]Nguồn: [cite: 10] "Dự đoán khả năng một trạng thái lượng tử trở thành hiện thực"
        Áp dụng: A (Bất thường tb) * E (Năng lượng tb) * C (Điều kiện địa chất).
        """
        return avg_anomaly * avg_energy * conditions

    @staticmethod
    def calculate_stability(destructive_force: float, resilience: float, noise: float, dampening: float) -> float:
        """
        Phái sinh từ Công thức Lò phản ứng UPT-RC (Stability Metric)
        k_eff = ... / (1 + noise + dampening)
        
        [cite_start]Nguồn: [cite: 169] Công thức k_eff trong lò phản ứng.
        Ý nghĩa: Mẫu số càng lớn (nhiễu + can thiệp), hệ thống càng ổn định (k_eff giảm).
        """
        numerator = destructive_force * resilience
        denominator = 1.0 + noise + dampening
        
        if denominator == 0: return 999.0 # Tránh chia cho 0
        return numerator / denominator