import asyncio
import random
import math
from datetime import datetime

class UPTReactorCore:
    """
    UPT-RC: Resonance Containment Reactor Core (Hard Sci-Fi Implementation)
    Dựa trên tài liệu: UPT_CompactNuclearReactor.pdf & UPT_QRS.pdf
    """
    # --- GOLDEN BUILD PARAMETERS (Thông số Vàng) ---
    CONST_C_GEO = 0.911      # Hệ số hình học tối ưu (Optimal Geometry)
    CONST_TAU_ION = 0.080    # Tỷ lệ nhiên liệu (Fuel Ratio)
    CONST_RES_FREQ = 2.148   # Tần số cộng hưởng (GHz)

    def __init__(self):
        # Trạng thái vận hành
        self.is_running = False
        self.status_code = "OFFLINE" # OFFLINE, STARTUP, NOMINAL, WARNING, CRITICAL, SCRAM
        
        # Các biến trạng thái vật lý (Physics State)
        self.core_temp = 300.0       # Kelvin (Ambient)
        self.neutron_flux = 0.0      # % Công suất (0-100%+)
        self.k_eff = 0.0             # Hệ số nhân hiệu dụng (Effective Multiplication Factor)
        self.r_plasma = 0.0          # Độ đồng bộ pha (Resonance Stability: 0.0 - 1.0)
        
        # Hệ thống điều khiển (Control Systems)
        self.control_rods = 100.0    # 100% = Full Damping (Tắt), 0% = Full Power
        self.cryo_cooling = 100.0    # Hệ thống làm mát (%)
        
        # Biến động môi trường (Environment)
        self.entropy_accumulation = 0.0
        self.phase_noise = 0.0       # Nhiễu pha (bao gồm tác động từ động đất)
        self.latest_disaster_impact = 0.0

    def start_reactor(self):
        """Khởi động quy trình đánh lửa (Ignition Sequence)"""
        if not self.is_running:
            self.is_running = True
            self.status_code = "STARTUP"
            print(f"☢️ [UPT-RC] Ignition Sequence Initiated. F_res locked at {self.CONST_RES_FREQ} GHz.")
            # Khởi tạo trạng thái ban đầu
            self.r_plasma = 0.5
            self.neutron_flux = 1.0 
            asyncio.create_task(self._run_simulation_loop())

    def trigger_phase_detuning(self):
        """
        Giao thức SCRAM: Phase De-tuning Shock.
        Phá vỡ cấu trúc cộng hưởng ngay lập tức để dừng phản ứng trong 1.5s.
        (Tham chiếu: UPT_FINAL.docx - Mục 14)
        """
        if self.status_code == "SCRAM": return
        
        print("🚨 [UPT-RC] EMERGENCY SCRAM INITIATED: PHASE DE-TUNING SHOCK!")
        self.status_code = "SCRAM"
        self.control_rods = 100.0 # Thả toàn bộ thanh điều khiển
        self.phase_noise = 10.0   # Bơm nhiễu cực đại
        self.r_plasma = 0.0       # Đánh sập đồng bộ pha

    def update_external_stress(self, stress_level: float):
        """Nhận dữ liệu động đất từ API và chuyển đổi thành Nhiễu Pha"""
        self.latest_disaster_impact = stress_level
        # Động đất gây rung chấn vật lý -> Tăng Phase Noise
        # Ví dụ: Mag 7.0 -> stress 0.7 -> noise tăng mạnh
        if stress_level > 0.5:
            print(f"⚠️ [UPT-RC] Seismic Activity Detected! External Phase Noise Rising: {stress_level}")

    async def _run_simulation_loop(self):
        """Vòng lặp vật lý thời gian thực (1Hz)"""
        while self.is_running:
            try:
                self._tick_physics()
                await asyncio.sleep(1)
            except Exception as e:
                print(f"⚠️ [REACTOR ERROR] {e}")
                await asyncio.sleep(1)

    def _tick_physics(self):
        """
        Tính toán vật lý lõi dựa trên công thức UPT.
        """
        # 0. Xử lý trạng thái SCRAM (Dập lò)
        if self.status_code == "SCRAM":
            self.neutron_flux *= 0.5 # Giảm lũy thừa
            self.core_temp += (300 - self.core_temp) * 0.1 # Nguội dần
            self.k_eff = 0
            if self.neutron_flux < 1.0:
                self.is_running = False
                self.status_code = "OFFLINE"
            return

        # 1. Tính toán Phase Noise (Nhiễu pha)
        # Noise = Quantum Fluctuations + External Disaster + Entropy
        quantum_noise = random.uniform(-0.01, 0.01)
        disaster_noise = self.latest_disaster_impact * 2.0 # Hệ số tác động của động đất
        
        self.phase_noise = abs(quantum_noise + disaster_noise + (self.entropy_accumulation / 100.0))

        # 2. Tính toán AI Dampening (Hệ số hãm từ thanh điều khiển)
        # Control rods càng cao -> Damping càng lớn
        ai_damp = (self.control_rods / 100.0) * 0.5

        # 3. CÔNG THỨC CHÍNH (Từ UPT_QRS.pdf): K_eff Calculation
        # k_eff = (E_p * C_geo * R_eff) / (1 + Noise + Damping)
        # Giả lập E_p (Energy Potential) dựa trên Flux hiện tại và Ion Fuel
        e_p = (self.neutron_flux / 50.0) + self.CONST_TAU_ION
        
        # R_eff (Hiệu suất cộng hưởng) phụ thuộc vào độ ổn định plasma hiện tại
        r_eff = self.r_plasma

        # Áp dụng công thức
        numerator = e_p * self.CONST_C_GEO * r_eff
        denominator = 1.0 + self.phase_noise + ai_damp
        
        self.k_eff = numerator / denominator if denominator > 0 else 0

        # 4. Cập nhật Neutron Flux (Dựa trên K_eff)
        # k_eff > 1: Flux tăng | k_eff < 1: Flux giảm
        if self.neutron_flux < 1.0: self.neutron_flux = 1.0 # Mồi lửa
        
        delta_flux = self.neutron_flux * (self.k_eff - 1.0) * 0.5 # Tốc độ phản ứng
        self.neutron_flux = max(0.0, self.neutron_flux + delta_flux)

        # 5. Cập nhật Nhiệt độ (Core Temp)
        # Nhiệt sinh ra tỷ lệ thuận với Flux, giải nhiệt tỷ lệ với Cryo Cooling
        heat_gen = self.neutron_flux * 5.0 
        cooling_cap = self.cryo_cooling * 4.0 # Khả năng làm mát
        
        self.core_temp += (heat_gen - cooling_cap) * 0.1
        if self.core_temp < 300: self.core_temp = 300 # Không thấp hơn nhiệt độ phòng

        # 6. Cập nhật R_plasma (Độ ổn định pha)
        # Nếu Flux quá cao hoặc Noise quá lớn -> R_plasma giảm (Mất đồng bộ)
        stability_delta = 0.01 # Tự phục hồi nhẹ
        if self.phase_noise > 0.1: stability_delta -= 0.05
        if self.neutron_flux > 120.0: stability_delta -= 0.02 # Quá tải
        
        self.r_plasma = max(0.0, min(1.0, self.r_plasma + stability_delta))

        # 7. Xác định trạng thái hệ thống (Status Code)
        if self.core_temp > 2500 or self.r_plasma < 0.2:
            self.status_code = "CRITICAL"
        elif self.core_temp > 1500 or self.r_plasma < 0.6:
            self.status_code = "WARNING"
        else:
            self.status_code = "NOMINAL"

        # Auto-safety: Nếu CRITICAL quá lâu -> Trigger SCRAM
        if self.status_code == "CRITICAL" and random.random() < 0.1:
            # AI Deloris tự động can thiệp
            self.trigger_phase_detuning()

    def get_status(self):
        """Trả về telemetry cho Frontend"""
        return {
            "timestamp": datetime.now().isoformat(),
            "status": self.status_code,
            "core_temp": round(self.core_temp, 1),
            "neutron_flux": round(self.neutron_flux, 2),
            "k_eff": round(self.k_eff, 4),
            "control_rods": round(self.control_rods, 1),
            "r_plasma": round(self.r_plasma, 4), # Quan trọng cho Visual
            "phase_noise": round(self.phase_noise, 3),
            "generated_power": round(self.neutron_flux * 5, 2) # Giả lập MW
        }

# Instance
upt_reactor = UPTReactorCore()