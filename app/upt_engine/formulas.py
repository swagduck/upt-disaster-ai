import math

class UPTMath:
    """
    Bộ công thức Toán học cho Unified Pulse Theory (UPT).
    Phiên bản: 4.0 (Cosmic-Geological Integrated)
    """

    @staticmethod
    def calculate_collapse_probability(anomaly_score: float, energy_level: float, geo_vulnerability: float) -> float:
        """P(φ) = A(t) * E(t) * C(t)"""
        a = max(0.0, min(1.0, anomaly_score))
        e = max(0.0, min(1.0, energy_level))
        c = max(0.0, min(1.0, geo_vulnerability))
        return a * e * c

    @staticmethod
    def calculate_resonance(sensors: list) -> float:
        """R(t) = Tích hợp cộng hưởng mạng lưới"""
        if not sensors: return 0.0
        total_anomaly = sum(s.get('anomaly_score', 0) for s in sensors)
        total_energy = sum(s.get('energy_level', 0) for s in sensors)
        return (total_anomaly * total_energy) / len(sensors)

    @staticmethod
    def calculate_stability(resonance: float, noise: float, dampening: float) -> float:
        """S = R / (1 + Noise + Damp)"""
        denominator = 1.0 + noise + dampening
        return resonance / denominator if denominator != 0 else 10.0

    # --- 👇 NÂNG CẤP NGHIÊM TÚC: CÔNG THỨC LIÊN KẾT VŨ TRỤ 👇 ---
    @staticmethod
    def calculate_geomagnetic_coupling(solar_class_energy: float, earth_field_strength: float = 1.0) -> float:
        """
        Tính toán 'Hệ số Liên kết Từ trường' (Coupling Coefficient).
        Mô tả: Năng lượng bão từ (Solar Flare) không tác động tức thời mà tạo ra 
        dao động trễ (Lagging Oscillation) lên lưới từ trường Trái Đất.
        
        Formula: Gamma_c = (E_solar ^ 1.5) * K_coupling
        """
        K_COUPLING = 0.15 # Hằng số liên kết UPT (Xác định từ thực nghiệm)
        
        # Năng lượng tia X (0.0 - 1.0) tác động theo hàm mũ
        impact = math.pow(solar_class_energy, 1.5) * K_COUPLING
        
        # Nếu từ trường Trái đất yếu đi (earth_field_strength < 1), tác động sẽ mạnh hơn
        final_impact = impact / earth_field_strength
        return min(final_impact, 2.0) # Giới hạn trần vật lý