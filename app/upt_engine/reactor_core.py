import math
import random

class UPTReactorCore:
    def __init__(self):
        # Thông số từ tài liệu UPT_FINAL.pdf
        self.f_res = 2.148  # Tần số cộng hưởng (GHz)
        self.k_p = 12.5     # Hệ số tăng cường
        self.target_coherence = 0.85 # Mục tiêu đồng bộ pha
        
        # Trạng thái hiện tại
        self.neutron_flux = 100.0
        self.temperature = 300.0 # Kelvin
        self.phase_noise = 0.0   # Mức nhiễu pha (để dập tắt phản ứng)

    def calculate_keff(self, ep_t: float, c_geo: float, r_eff: float, ai_damp: float):
        """
        Tính hệ số nhân hiệu dụng (k_eff) dựa trên công thức UPT-RC:
        k_eff = (Ep(t) * C_geo * R_eff(t)) / (1 + Tau_noise + AI_damp)
        """
        numerator = ep_t * c_geo * r_eff
        denominator = 1 + self.phase_noise + ai_damp
        
        # Tránh chia cho 0
        if denominator == 0:
            return 9999.0
            
        return numerator / denominator

    def simulate_step(self, entropy_input: float, ai_intervention: bool):
        """
        Mô phỏng 1 chu kỳ lò phản ứng (PHIÊN BẢN OVERCLOCK)
        """
        
        # 1. Tính toán nhiễu loạn ngẫu nhiên
        base_fluctuation = random.uniform(-0.02, 0.05) # Thiên về tăng trưởng dương
        
        # [QUAN TRỌNG] Logic mới:
        # Entropy càng THẤP (trật tự) -> Ep càng CAO (Cộng hưởng mạnh)
        # 1.05 là mức cơ bản. Nếu Entropy=0 -> Ep = 1.15 (Tăng trưởng 15%/bước)
        # Nếu Entropy=1 -> Ep = 0.65 (Tắt ngóm)
        current_ep = 1.05 + base_fluctuation - (entropy_input * 0.4)
        
        # 2. Logic AI "Deloris" tự vệ
        ai_damp = 0.0
        status = "STABLE"
        
        if ai_intervention:
            # Ngưỡng kích hoạt: Flux > 200 (Cho phép chạy đà lâu hơn chút)
            if self.neutron_flux > 200.0:
                ai_damp = 0.5 # Damping nhẹ để kìm hãm
                self.phase_noise += 0.5 # Bơm nhiễu tích lũy
                status = "DAMPING_ACTIVE"
            elif self.neutron_flux < 80.0:
                # Cơ chế tự phục hồi phase khi lò nguội
                self.phase_noise = max(0, self.phase_noise - 0.2)
                if self.phase_noise == 0:
                    status = "RECOVERING"
                else:
                    status = "COOLING_DOWN"
        
        # 3. Tính k_eff
        # R_eff cũng bị giảm nếu entropy cao
        r_eff_current = max(0, 1.0 - (entropy_input * 0.1))
        
        k_eff = self.calculate_keff(current_ep, 1.0, r_eff_current, ai_damp)
        
        # 4. Cập nhật trạng thái lò
        self.neutron_flux = self.neutron_flux * k_eff
        
        # Giới hạn trần/sàn để không bị lỗi số học
        self.neutron_flux = max(0.1, min(self.neutron_flux, 50000.0))
        
        # Nhiệt độ: 300K nền + Flux * 10 (Nóng nhanh hơn)
        self.temperature = 300 + (self.neutron_flux * 10)

        return {
            "timestamp": "Now",
            "k_eff": round(k_eff, 4),
            "neutron_flux": round(self.neutron_flux, 2),
            "core_temp": round(self.temperature, 1),
            "status": status,
            "phase_noise_level": round(self.phase_noise, 2)
        }