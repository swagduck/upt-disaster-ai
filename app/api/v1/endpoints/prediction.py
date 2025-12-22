from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

# Import Service và Engine
from app.services.earthquake_service import DisasterService
from app.upt_engine.formulas import UPTMath

router = APIRouter()

# --- 1. DEFINITIONS (Mô hình dữ liệu) ---
class SensorData(BaseModel):
    station_id: str
    energy_level: float 
    anomaly_score: float
    location_weight: float = 1.0

class PredictionRequest(BaseModel):
    region_name: str
    sensors: List[SensorData]
    geo_vulnerability: float
    environmental_noise: float = 0.1
    active_dampening: float = 0.0

# --- 2. API ENDPOINTS ---

# API 1: Dự báo thủ công (Dành cho Simulation Mode trên Web)
@router.post("/predict")
async def predict_disaster(request: PredictionRequest):
    # Tính trung bình các chỉ số đầu vào
    if not request.sensors:
        return {"error": "No sensor data provided"}
        
    avg_energy = sum(s.energy_level for s in request.sensors) / len(request.sensors)
    avg_anomaly = sum(s.anomaly_score for s in request.sensors) / len(request.sensors)
    
    # BƯỚC 1: Tính xác suất sụp đổ (P)
    prob_index = UPTMath.calculate_collapse_probability(
        avg_anomaly, avg_energy, request.geo_vulnerability
    )
    
    # BƯỚC 2: Tính cộng hưởng (R)
    resonance = UPTMath.calculate_resonance(request.sensors)
    
    # BƯỚC 3: Tính độ ổn định (S) - Truyền đủ 3 tham số: resonance, noise, dampening
    stability = UPTMath.calculate_stability(
        resonance, request.environmental_noise, request.active_dampening
    )
    
    # Logic Cảnh báo
    alert = "NORMAL"
    recommendation = "Hệ thống ổn định. Tiếp tục giám sát."
    
    if prob_index > 0.4:
        alert = "WARNING"
        recommendation = "Cảnh báo: Dao động bất thường. Chuẩn bị quy trình ứng phó."
    
    if prob_index > 0.7:
        alert = "CRITICAL"
        recommendation = "KÍCH HOẠT SƠ TÁN NGAY LẬP TỨC. Sụp đổ lượng tử sắp xảy ra."

    return {
        "region": request.region_name,
        "probability_index": prob_index,
        "network_resonance": resonance,
        "stability_score": stability,
        "alert_level": alert,
        "action_recommendation": recommendation
    }

# API 2: Dự báo Thời gian thực (Kết nối USGS + NASA + Telegram)
@router.get("/realtime/usgs")
async def get_realtime_prediction():
    # 1. Gọi Service lấy dữ liệu thật (Sử dụng await vì hàm fetch giờ là async)
    real_sensors = await DisasterService.fetch_all_realtime()
    
    if not real_sensors:
        return {
            "message": "Không có dữ liệu vệ tinh hoặc lỗi kết nối.",
            "upt_metrics": None,
            "raw_sensors": []
        }

    # 2. Tính toán chỉ số UPT trung bình toàn cầu
    avg_energy = sum(s['energy_level'] for s in real_sensors) / len(real_sensors)
    avg_anomaly = sum(s['anomaly_score'] for s in real_sensors) / len(real_sensors)
    
    # Giả định Geo Vulnerability trung bình là 0.5
    prob_index = UPTMath.calculate_collapse_probability(avg_anomaly, avg_energy, 0.5)
    
    # Ước lượng cộng hưởng (vì real_sensors là dict, không phải object SensorData)
    # Ta dùng công thức đơn giản hóa cho realtime: R = Anomaly * Energy * Factor
    resonance = avg_anomaly * avg_energy * 1.5 
    
    # Tính độ ổn định (S) với noise mặc định 0.1 và dampening 0.0
    stability = UPTMath.calculate_stability(resonance, 0.1, 0.0)
    
    # Logic Alert
    alert = "NORMAL"
    if prob_index > 0.45: alert = "WARNING"
    if prob_index > 0.75: alert = "CRITICAL"

    return {
        "source": "USGS Seismic & NASA EONET",
        "detected_events": len(real_sensors),
        "upt_metrics": {
            "probability_index": prob_index,
            "network_resonance": resonance,
            "stability_score": stability,
            "alert_level": alert
        },
        "raw_sensors": real_sensors
    }