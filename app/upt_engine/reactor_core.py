import asyncio
import random
import math
from datetime import datetime

class UPTReactorCore:
    def __init__(self):
        # Trạng thái khởi tạo của Lò phản ứng
        self.is_running = False
        self.core_temp = 300.0       # Kelvin (300K ~ 27°C)
        self.neutron_flux = 100.0    # Đơn vị ảo
        self.k_eff = 0.98            # Hệ số nhân nơ-tron
        self.control_rods = 50.0     # % Thanh điều khiển (50% là an toàn)
        self.coolant_pressure = 150.0 # Bar
        self.entropy_accumulation = 0.0
        
        # Cache dữ liệu thảm họa để ảnh hưởng đến lò
        self.latest_disaster_impact = 0.0

    def start_reactor(self):
        """Khởi động quy trình nền mô phỏng lò phản ứng"""
        if not self.is_running:
            self.is_running = True
            print("☢️ [REACTOR] Core ignition sequence initiated...")
            asyncio.create_task(self._run_simulation_loop())

    async def _run_simulation_loop(self):
        """Vòng lặp vô tận mô phỏng vật lý hạt nhân (Giả lập)"""
        while self.is_running:
            try:
                self._tick_physics()
                await asyncio.sleep(1) # Cập nhật mỗi giây
            except Exception as e:
                print(f"⚠️ [REACTOR ERROR] {e}")
                await asyncio.sleep(5)

    def _tick_physics(self):
        """Tính toán biến động chỉ số mỗi giây"""
        # 1. Biến động ngẫu nhiên (Quantum Noise)
        noise = random.uniform(-0.5, 0.5)
        
        # 2. Ảnh hưởng từ dữ liệu thảm họa bên ngoài (nếu có)
        # Nếu có động đất lớn, lò sẽ mất ổn định nhẹ
        external_stress = self.latest_disaster_impact * 5.0
        
        # 3. Tính toán nhiệt độ (Core Temp)
        # Nhiệt độ tăng nếu thanh điều khiển rút ra (control_rods giảm)
        target_temp = 300 + (100 - self.control_rods) * 10 + external_stress
        self.core_temp += (target_temp - self.core_temp) * 0.1 + noise

        # 4. Tính toán thông lượng nơ-tron (Flux)
        flux_delta = (100 - self.control_rods) * 0.5 + noise * 2
        self.neutron_flux = max(0, min(2000, self.neutron_flux + flux_delta - 1.0))

        # 5. Hệ số K-effective (Độ ổn định)
        # K > 1: Quá tải (Supercritical) | K < 1: Tắt dần | K = 1: Ổn định
        if self.control_rods > 60:
            target_k = 0.95
        elif self.control_rods < 40:
            target_k = 1.05
        else:
            target_k = 1.00
            
        self.k_eff += (target_k - self.k_eff) * 0.05

        # Tự động làm mát nếu quá nóng (Safety System)
        if self.core_temp > 1500:
            self.control_rods = min(100, self.control_rods + 5) # Hạ thanh điều khiển khẩn cấp

    def update_external_stress(self, stress_level: float):
        """API gọi hàm này để báo cho lò biết thế giới đang hỗn loạn"""
        self.latest_disaster_impact = stress_level

    def get_status(self):
        """Trả về trạng thái hiện tại cho API/WebSocket"""
        status_level = "NOMINAL"
        if self.core_temp > 1000: status_level = "WARNING"
        if self.core_temp > 2000: status_level = "CRITICAL"

        return {
            "timestamp": datetime.now().isoformat(),
            "status": status_level,
            "core_temp": round(self.core_temp, 2),
            "neutron_flux": round(self.neutron_flux, 2),
            "k_eff": round(self.k_eff, 4),
            "control_rods": round(self.control_rods, 1),
            "entropy": round(self.entropy_accumulation, 2)
        }

# --- QUAN TRỌNG: KHỞI TẠO INSTANCE ---
# Đây là biến mà main.py đang tìm kiếm nhưng không thấy
upt_reactor = UPTReactorCore()