import math

class UPTMath:
    """
    Bộ công thức Toán học cho Lý thuyết Unified Pulse Theory (UPT)
    """

    @staticmethod
    def calculate_collapse_probability(anomaly_score: float, energy_level: float, geo_vulnerability: float) -> float:
        """
        Công thức Sụp đổ Xác suất: P(φ) = A(t) * E(t) * C(t)
        """
        # Đảm bảo giá trị nằm trong khoảng [0, 1]
        a = max(0.0, min(1.0, anomaly_score))
        e = max(0.0, min(1.0, energy_level))
        c = max(0.0, min(1.0, geo_vulnerability))
        
        return a * e * c

    @staticmethod
    def calculate_resonance(sensors: list) -> float:
        """
        Tính Cộng hưởng Mạng lưới R(t)
        R(t) = (Tổng Anomaly * Tổng Energy) / Số lượng cảm biến
        """
        if not sensors:
            return 0.0
        
        total_anomaly = sum(s.anomaly_score if hasattr(s, 'anomaly_score') else s['anomaly_score'] for s in sensors)
        total_energy = sum(s.energy_level if hasattr(s, 'energy_level') else s['energy_level'] for s in sensors)
        n = len(sensors)
        
        # Công thức cộng hưởng đơn giản hóa
        return (total_anomaly * total_energy) / n

    @staticmethod
    def calculate_stability(resonance: float, noise: float, dampening: float) -> float:
        """
        Tính độ Ổn định (Stability Score)
        S = Resonance / (1 + Noise + Dampening)
        """
        numerator = resonance
        denominator = 1.0 + noise + dampening
        
        if denominator == 0:
            return 10.0 # Tránh chia cho 0, trả về giá trị rủi ro cao nhất
            
        return numerator / denominator