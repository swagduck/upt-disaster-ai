import requests
import time
import sys

# URL của API (Đảm bảo server đang chạy ở port 8000)
URL = "http://localhost:8000/api/v1/reactor/simulate"

def print_status(step, data):
    # Tạo màu cho đẹp (ANSI escape codes)
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    
    temp = data.get('core_temp', 0)
    flux = data.get('neutron_flux', 0)
    status = data.get('status', 'UNKNOWN')
    phase = data.get('phase_noise_level', 0)
    
    # Chọn màu dựa trên nhiệt độ
    color = GREEN
    if temp > 1000: color = YELLOW
    if temp > 1800: color = RED
    
    # In ra dòng trạng thái
    print(f"STEP {step:02d} | "
          f"TEMP: {color}{temp:6.1f} K{RESET} | "
          f"FLUX: {color}{flux:6.2f}{RESET} | "
          f"NOISE: {phase} | "
          f"STATUS: {status}")

def run_simulation():
    print("--- BẮT ĐẦU KÍCH THÍCH LÒ PHẢN ỨNG (ENTROPY = 0) ---")
    print("Mục tiêu: Đẩy Flux lên cao để kích hoạt AI Safety")
    
    # 1. Giai đoạn tăng nhiệt (30 lần gọi)
    for i in range(1, 40):
        try:
            # Gửi entropy = 0.0 (Cộng hưởng hoàn hảo -> Nóng lên)
            response = requests.post(URL, json={"entropy_inject": 0.0, "enable_ai_safety": true})
            if response.status_code == 200:
                print_status(i, response.json())
            else:
                print("Error:", response.text)
            
            # Nghỉ xíu để kịp nhìn
            time.sleep(0.2)
            
        except Exception as e:
            print("Kết nối thất bại. Server có chạy không?")
            break

if __name__ == "__main__":
    # Sửa lỗi true/True của Python vs JSON
    true = True 
    run_simulation()