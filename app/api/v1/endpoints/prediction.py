from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
# Import Class mới từ file service
from app.services.earthquake_service import DisasterService 
from app.upt_engine.formulas import UPTMath

router = APIRouter()

# Mô hình dữ liệu đầu vào (cho chế độ Manual)
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

# API 1: Dự báo thủ công (Manual)
@router.post("/predict")
async def predict_disaster(request: PredictionRequest):
    # Tính trung bình các chỉ số từ sensors gửi lên
    avg_energy = sum(s.energy_level for s in request.sensors) / len(request.sensors)
    avg_anomaly = sum(s.anomaly_score for s in request.sensors) / len(request.sensors)
    
    # 1. Tính xác suất sụp đổ (UPT Probability)
    prob_index = UPTMath.calculate_collapse_probability(
        avg_anomaly, avg_energy, request.geo_vulnerability
    )
    
    # 2. Tính cộng hưởng (Resonance)
    resonance = UPTMath.calculate_resonance(request.sensors)
    
    # 3. Tính độ ổn định (Stability)
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

# API 2: Dự báo Thời gian thực (Real-time Satellite)
@router.get("/realtime/usgs")
async def get_realtime_prediction():
    # 1. Lấy dữ liệu đa nguồn (USGS + NASA)
    real_sensors = DisasterService.fetch_all_realtime()
    
    if not real_sensors:
        return {"message": "Không có dữ liệu vệ tinh hoặc lỗi kết nối."}

    # 2. Tính toán UPT trên dữ liệu thật
    # (Lấy trung bình nhanh để đưa ra chỉ số toàn cầu)
    avg_energy = sum(s['energy_level'] for s in real_sensors) / len(real_sensors)
    avg_anomaly = sum(s['anomaly_score'] for s in real_sensors) / len(real_sensors)
    
    # Giả định Geo Vulnerability trung bình là 0.5 cho toàn cầu
    prob_index = UPTMath.calculate_collapse_probability(avg_anomaly, avg_energy, 0.5)
    
    # Mock object resonance (vì hàm resonance cần object có thuộc tính)
    resonance = avg_anomaly * 1.5 # Ước lượng nhanh cộng hưởng
    
    stability = UPTMath.calculate_stability(resonance, 0.1, 0.0)
    
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