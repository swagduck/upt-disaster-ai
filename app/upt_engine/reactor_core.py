import asyncio
import random
import math
from datetime import datetime

class UPTReactorCore:
    """
    UPT-RC: Resonance Containment Reactor Core (Production Grade)
    """
    # GOLDEN BUILD PARAMETERS
    CONST_C_GEO = 0.911
    CONST_TAU_ION = 0.080
    CONST_RES_FREQ = 2.148

    def __init__(self):
        self.is_running = False
        self.status_code = "OFFLINE"
        
        # Physics State
        self.core_temp = 300.0
        self.neutron_flux = 0.0
        self.k_eff = 0.0
        self.r_plasma = 0.0
        
        # Control Systems
        self.control_rods = 100.0
        self.cryo_cooling = 100.0
        
        # Environment & Noise
        self.entropy_accumulation = 0.0
        self.phase_noise = 0.0
        
        # --- 👇 NÂNG CẤP: BIẾN TRẠNG THÁI TỪ TRƯỜNG TỒN DƯ 👇 ---
        # Bão mặt trời gây ra nhiễu từ trường tồn dư, giảm rất chậm theo thời gian
        self.geomagnetic_residual = 0.0 

    def start_reactor(self):
        if not self.is_running:
            self.is_running = True
            self.status_code = "STARTUP"
            print(f"☢️ [UPT-RC] Ignition Sequence Initiated. F_res locked at {self.CONST_RES_FREQ} GHz.")
            self.r_plasma = 0.5
            self.neutron_flux = 1.0 
            asyncio.create_task(self._run_simulation_loop())

    def trigger_phase_detuning(self):
        if self.status_code == "SCRAM": return
        print("🚨 [UPT-RC] EMERGENCY SCRAM: PHASE DE-TUNING SHOCK EXECUTED!")
        self.status_code = "SCRAM"
        self.control_rods = 100.0
        self.phase_noise = 10.0
        self.r_plasma = 0.0

    # --- 👇 NÂNG CẤP: HÀM TIÊM NHIỄU VŨ TRỤ (COSMIC INJECTION) 👇 ---
    def inject_cosmic_interference(self, coupling_factor: float):
        """
        Nhận tín hiệu từ Bão Mặt Trời.
        Thay vì gây sốc ngay, nó tích tụ vào 'Geomagnetic Residual'.
        Đây là hiệu ứng 'Cánh bướm' - tích tụ năng lượng ngầm.
        """
        if coupling_factor > 0.05:
            print(f"⚠️ [UPT-RC] COSMIC INTERFERENCE DETECTED. Coupling Factor: {coupling_factor:.4f}")
            # Tích tụ năng lượng vào từ trường tồn dư
            self.geomagnetic_residual += coupling_factor

    def update_external_stress(self, stress_level: float):
        # Tác động vật lý trực tiếp (Động đất)
        if stress_level > 0.5:
            print(f"⚠️ [UPT-RC] Seismic Wave Impact: {stress_level}")
            self.phase_noise += stress_level * 0.5

    async def _run_simulation_loop(self):
        while self.is_running:
            try:
                self._tick_physics()
                await asyncio.sleep(1)
            except Exception as e:
                print(f"⚠️ [REACTOR ERROR] {e}")
                await asyncio.sleep(1)

    def _tick_physics(self):
        if self.status_code == "SCRAM":
            self.neutron_flux *= 0.5
            self.core_temp += (300 - self.core_temp) * 0.1
            self.k_eff = 0
            if self.neutron_flux < 1.0:
                self.is_running = False
                self.status_code = "OFFLINE"
            return

        # 1. Physics: Phân rã từ trường tồn dư (Decay)
        # Bão từ tan rất chậm (giảm 1% mỗi giây) -> Gây bất ổn dài hạn
        self.geomagnetic_residual *= 0.99 

        # 2. Physics: Tính toán Phase Noise tổng hợp
        quantum_noise = random.uniform(-0.01, 0.01)
        
        # Noise = Quantum + (Residual Magnetic * 2.0)
        # Từ trường tồn dư càng cao, noise nền càng lớn
        self.phase_noise = abs(quantum_noise + (self.geomagnetic_residual * 2.0))
        
        # Tự động xả bớt Noise nếu quá cao (nhờ hệ thống ổn định)
        if self.phase_noise > 2.0: self.phase_noise *= 0.9

        # 3. K_eff Calculation (UPT Formula)
        ai_damp = (self.control_rods / 100.0) * 0.5
        e_p = (self.neutron_flux / 50.0) + self.CONST_TAU_ION
        r_eff = self.r_plasma

        numerator = e_p * self.CONST_C_GEO * r_eff
        denominator = 1.0 + self.phase_noise + ai_damp
        self.k_eff = numerator / denominator if denominator > 0 else 0

        # 4. Neutron Flux Dynamics
        if self.neutron_flux < 1.0: self.neutron_flux = 1.0
        delta_flux = self.neutron_flux * (self.k_eff - 1.0) * 0.5
        self.neutron_flux = max(0.0, self.neutron_flux + delta_flux)

        # 5. Thermodynamics
        heat_gen = self.neutron_flux * 5.0 
        cooling_cap = self.cryo_cooling * 4.0
        self.core_temp += (heat_gen - cooling_cap) * 0.1
        if self.core_temp < 300: self.core_temp = 300

        # 6. Resonance Stability (R_plasma)
        # Nếu bị nhiễm từ (geomagnetic_residual cao), R_plasma rất khó hồi phục 1.0
        stability_delta = 0.01
        if self.phase_noise > 0.1: stability_delta -= 0.05
        
        self.r_plasma = max(0.0, min(1.0, self.r_plasma + stability_delta))

        # 7. Status Logic
        if self.core_temp > 2500 or self.r_plasma < 0.2:
            self.status_code = "CRITICAL"
        elif self.core_temp > 1500 or self.r_plasma < 0.6 or self.geomagnetic_residual > 0.5:
            # Thêm trạng thái WARNING nếu nhiễm từ cao
            self.status_code = "WARNING"
        else:
            self.status_code = "NOMINAL"

        # Safety Protocol
        if self.status_code == "CRITICAL" and random.random() < 0.1:
            self.trigger_phase_detuning()

    def get_status(self):
        return {
            "timestamp": datetime.now().isoformat(),
            "status": self.status_code,
            "core_temp": round(self.core_temp, 1),
            "neutron_flux": round(self.neutron_flux, 2),
            "k_eff": round(self.k_eff, 4),
            "control_rods": round(self.control_rods, 1),
            "r_plasma": round(self.r_plasma, 4),
            "phase_noise": round(self.phase_noise, 3),
            "generated_power": round(self.neutron_flux * 5, 2),
            # Thêm chỉ số mới để theo dõi trên Frontend (nếu cần)
            "magnetic_residual": round(self.geomagnetic_residual, 3)
        }

upt_reactor = UPTReactorCore()