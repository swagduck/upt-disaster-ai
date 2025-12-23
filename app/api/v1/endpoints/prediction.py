from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

# Import Service và Engine
from app.services.earthquake_service import DisasterService
from app.upt_engine.formulas import UPTMath
from app.upt_engine.neural_core import guardian_brain # <--- IMPORT MỚI

router = APIRouter()

# --- DEFINITIONS ---
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

# Model mới cho Neural Request
class NeuralPredictionRequest(BaseModel):
    lat: float
    lon: float
    simulated_energy: float = 0.5

# --- API ENDPOINTS ---

# 1. API CŨ: Dự báo công thức (Giữ nguyên cho tính tương thích)
@router.post("/predict")
async def predict_disaster(request: PredictionRequest):
    if not request.sensors:
        return {"error": "No sensor data provided"}
    
    avg_energy = sum(s.energy_level for s in request.sensors) / len(request.sensors)
    avg_anomaly = sum(s.anomaly_score for s in request.sensors) / len(request.sensors)
    
    prob_index = UPTMath.calculate_collapse_probability(avg_anomaly, avg_energy, request.geo_vulnerability)
    resonance = UPTMath.calculate_resonance(request.sensors)
    stability = UPTMath.calculate_stability(resonance, request.environmental_noise, request.active_dampening)
    
    alert = "NORMAL"
    recommendation = "Hệ thống ổn định."
    if prob_index > 0.4: alert = "WARNING"; recommendation = "Dao động bất thường."
    if prob_index > 0.7: alert = "CRITICAL"; recommendation = "SƠ TÁN NGAY LẬP TỨC."

    return {
        "region": request.region_name,
        "probability_index": prob_index,
        "network_resonance": resonance,
        "stability_score": stability,
        "alert_level": alert,
        "action_recommendation": recommendation
    }

# 2. API CŨ: Realtime USGS (Giữ nguyên)
@router.get("/realtime/usgs")
async def get_realtime_prediction():
    real_sensors = await DisasterService.fetch_all_realtime()
    if not real_sensors:
        return {"message": "No data.", "upt_metrics": None, "raw_sensors": []}

    avg_energy = sum(s['energy_level'] for s in real_sensors) / len(real_sensors)
    avg_anomaly = sum(s['anomaly_score'] for s in real_sensors) / len(real_sensors)
    
    prob_index = UPTMath.calculate_collapse_probability(avg_anomaly, avg_energy, 0.5)
    resonance = avg_anomaly * avg_energy * 1.5 
    stability = UPTMath.calculate_stability(resonance, 0.1, 0.0)
    
    alert = "NORMAL"
    if prob_index > 0.45: alert = "WARNING"
    if prob_index > 0.75: alert = "CRITICAL"

    return {
        "source": "USGS & NASA",
        "detected_events": len(real_sensors),
        "upt_metrics": {
            "probability_index": prob_index,
            "network_resonance": resonance,
            "stability_score": stability,
            "alert_level": alert
        },
        "raw_sensors": real_sensors
    }

# --- 3. CÁC API AI MỚI (NEURAL CORE) ---

@router.get("/status")
async def get_ai_status():
    """Kiểm tra trạng thái bộ não AI"""
    return {
        "status": "ONLINE" if guardian_brain.is_trained else "INITIALIZING",
        "knowledge_base_size": len(guardian_brain.X_buffer),
        "model_type": "RandomForestRegressor (Scikit-Learn)"
    }

@router.post("/train")
async def trigger_training():
    """Kích hoạt AI học từ dữ liệu cache hiện tại"""
    current_data = DisasterService.get_latest_data()
    if not current_data:
        return {"message": "No realtime data available to learn from."}
    
    count = guardian_brain.learn(current_data)
    return {
        "message": "Neural Core updated successfully.", 
        "total_events_learned": count,
        "source_events": len(current_data)
    }

@router.post("/forecast")
async def forecast_disaster(req: NeuralPredictionRequest):
    """Dự báo rủi ro tại tọa độ cụ thể bằng AI"""
    # Anomaly mặc định là 0.5 (trung bình) cho vùng chưa biết
    risk = guardian_brain.predict_risk(req.lat, req.lon, req.simulated_energy, 0.5)
    
    alert_level = "NORMAL"
    if risk > 0.5: alert_level = "WARNING"
    if risk > 0.8: alert_level = "CRITICAL"
    
    return {
        "location": {"lat": req.lat, "lon": req.lon},
        "predicted_risk": risk,
        "alert_level": alert_level,
        "ai_confidence": 0.92 # Confidence giả lập
    }