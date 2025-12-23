import math
import random

class UPTReactorCore:
    def __init__(self):
        # Thông số UPT
        self.f_res = 2.148
        self.k_p = 12.5
        self.target_coherence = 0.85
        
        # Trạng thái
        self.neutron_flux = 100.0
        self.temperature = 300.0 
        self.phase_noise = 0.0
        
        # Biến đệm để lưu cú sốc
        self._shock_buffer = 0.0

    def calculate_keff(self, ep_t: float, c_geo: float, r_eff: float, ai_damp: float):
        numerator = ep_t * c_geo * r_eff
        denominator = 1 + self.phase_noise + ai_damp
        if denominator == 0: return 9999.0
        return numerator / denominator

    def simulate_step(self, entropy_input: float, ai_intervention: bool, external_shock: float = 0.0):
        """
        Mô phỏng 1 bước.
        external_shock: Giá trị từ 0.0 - 1.0 (Động đất bên ngoài tác động vào lò)
        """
        
        # Xử lý sốc ngoại lai (tích lũy)
        if external_shock > 0:
            self._shock_buffer += external_shock * 10.0 # Nhân hệ số để thấy rõ tác động
            
        # Giảm dần sốc theo thời gian (Hồi phục)
        current_shock = self._shock_buffer
        self._shock_buffer = max(0, self._shock_buffer - 0.5)

        # 1. Biến động cơ bản
        base_fluctuation = random.uniform(-0.02, 0.05)
        
        # Shock làm tăng entropy (giảm Ep) nhưng lại tăng phase_noise cực mạnh
        current_ep = 1.05 + base_fluctuation - (entropy_input * 0.4)
        
        # 2. Logic AI Safety
        ai_damp = 0.0
        status = "STABLE"
        
        # Nếu có shock, lò bị rung lắc pha (Phase Noise tăng vọt)
        if current_shock > 0:
            self.phase_noise += current_shock * 0.2
            status = "SEISMIC WARNING"

        if ai_intervention:
            if self.neutron_flux > 200.0 or self.phase_noise > 2.0:
                ai_damp = 0.8 # Can thiệp mạnh hơn
                self.phase_noise += 0.1 
                status = "DAMPING_ACTIVE"
            elif self.neutron_flux < 80.0 and current_shock == 0:
                self.phase_noise = max(0, self.phase_noise - 0.2)
                status = "RECOVERING" if self.phase_noise == 0 else "COOLING_DOWN"
        
        # 3. Tính toán
        r_eff_current = max(0, 1.0 - (entropy_input * 0.1))
        k_eff = self.calculate_keff(current_ep, 1.0, r_eff_current, ai_damp)
        
        self.neutron_flux = self.neutron_flux * k_eff
        self.neutron_flux = max(0.1, min(self.neutron_flux, 50000.0))
        self.temperature = 300 + (self.neutron_flux * 10) + (current_shock * 100)

        # Cảnh báo nóng chảy
        if self.temperature > 1500: status = "CRITICAL TEMP"
        if self.temperature > 2500: status = "MELTDOWN IMMINENT"

        return {
            "timestamp": "Now",
            "k_eff": round(k_eff, 4),
            "neutron_flux": round(self.neutron_flux, 2),
            "core_temp": round(self.temperature, 1),
            "status": status,
            "phase_noise_level": round(self.phase_noise, 2)
        }