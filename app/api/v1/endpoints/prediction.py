from fastapi import APIRouter, Depends, Request
import math
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from fastapi_cache.decorator import cache
from fastapi import BackgroundTasks
from typing import List, Optional

from app.services.earthquake_service import DisasterService
from app.upt_engine.formulas import UPTMath
from app.upt_engine.deep_core import guardian_brain
from app.core.logger import get_logger
from app.core.limiter import limiter
from app.core.security import require_api_key

logger = get_logger(__name__)
router = APIRouter()


# ── Request Models ────────────────────────────────────────────────────────────
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


class NeuralPredictionRequest(BaseModel):
    lat: float
    lon: float
    simulated_energy: float = 0.5


# ── Helper ────────────────────────────────────────────────────────────────────
def _haversine_km(lat1, lon1, lat2, lon2):
    """Tính khoảng cách (km) giữa 2 toạ độ trên mặt cầu."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def _calc_local_energy(lat: float, lon: float, events: list, radius_km: float = 800.0) -> float:
    """Tính mức năng lượng cục bộ thực tế tại toạ độ (lat, lon)."""
    total = 0.0
    for e in events:
        e_lat = e.get("lat")
        e_lon = e.get("lon")
        if e_lat is None or e_lon is None:
            continue
        dist = _haversine_km(lat, lon, e_lat, e_lon)
        if dist < radius_km:
            energy = e.get("energy_level", 0.0)
            impact = energy * (1 - dist / radius_km)
            total += max(0.0, impact)
    # Dùng log1p để tránh bão hòa (saturation) ở các khu vực nhiều động đất nhỏ
    # log1p(x) / log1p(10) cho phép khoảng 10 đơn vị năng lượng = 1.0
    return min(math.log1p(total) / math.log1p(10), 1.0)

@router.post("/predict")
async def predict_disaster(request: PredictionRequest):
    """Formula-based disaster probability (kept for backwards compatibility)."""
    if not request.sensors:
        logger.warning("[PREDICTION API] /predict called with no sensor data.")
        return {"error": "No sensor data provided"}

    avg_energy = sum(s.energy_level for s in request.sensors) / len(request.sensors)
    avg_anomaly = sum(s.anomaly_score for s in request.sensors) / len(request.sensors)

    prob_index = UPTMath.calculate_collapse_probability(
        avg_anomaly, avg_energy, request.geo_vulnerability
    )
    sensor_dicts = [s.model_dump() for s in request.sensors]
    resonance = UPTMath.calculate_resonance(sensor_dicts)
    stability = UPTMath.calculate_stability(
        resonance, request.environmental_noise, request.active_dampening
    )

    alert = "NORMAL"
    recommendation = "Hệ thống ổn định."
    if prob_index > 0.4:
        alert = "WARNING"
        recommendation = "Dao động bất thường."
    if prob_index > 0.7:
        alert = "CRITICAL"
        recommendation = "SƠ TÁN NGAY LẬP TỨC."

    logger.info(
        f"[PREDICTION API] Formula prediction for '{request.region_name}': "
        f"P={prob_index:.3f} | Alert={alert}"
    )
    return {
        "region": request.region_name,
        "probability_index": prob_index,
        "network_resonance": resonance,
        "stability_score": stability,
        "alert_level": alert,
        "action_recommendation": recommendation,
    }


@router.get("/realtime/usgs")
@cache(expire=30)
async def get_realtime_prediction():
    """Fetch live USGS + NASA data and compute UPT metrics."""
    real_sensors = await DisasterService.fetch_all_realtime()
    if not real_sensors:
        logger.warning("[PREDICTION API] /realtime/usgs returned no sensor data.")
        return {"message": "No data.", "upt_metrics": None, "raw_sensors": []}

    avg_energy = sum(s["energy_level"] for s in real_sensors) / len(real_sensors)
    avg_anomaly = sum(s["anomaly_score"] for s in real_sensors) / len(real_sensors)

    prob_index = UPTMath.calculate_collapse_probability(avg_anomaly, avg_energy, 0.5)
    resonance = avg_anomaly * avg_energy * 1.5
    stability = UPTMath.calculate_stability(resonance, 0.1, 0.0)

    alert = "NORMAL"
    if prob_index > 0.45: alert = "WARNING"
    if prob_index > 0.75: alert = "CRITICAL"

    logger.info(
        f"[PREDICTION API] Realtime: {len(real_sensors)} events | "
        f"P={prob_index:.3f} | Alert={alert}"
    )
    return {
        "source": "USGS & NASA",
        "detected_events": len(real_sensors),
        "upt_metrics": {
            "probability_index": prob_index,
            "network_resonance": resonance,
            "stability_score": stability,
            "alert_level": alert,
        },
        "raw_sensors": real_sensors,
    }


@router.get("/status")
@cache(expire=60)
async def get_ai_status():
    """Return the current state of the Guardian AI brain."""
    return {
        "status": "ONLINE" if guardian_brain.is_trained else "INITIALIZING",
        "buffer_size": len(guardian_brain.realtime_buffer),
        "model_type": "Gradient Boosting (Scikit-Learn)",
    }

@router.get("/evaluation")
async def get_ai_evaluation():
    """Return the current accuracy metrics of the Guardian AI."""
    if not guardian_brain.is_trained:
        return {"status": "NO_DATA", "message": "Model has not been trained yet."}
    return {
        "status": "EVALUATED",
        "metrics": guardian_brain.metrics
    }


@router.post("/train", dependencies=[Depends(require_api_key)])
@limiter.limit("5/minute")
async def trigger_training(request: Request):
    """Force the AI to learn from the current realtime cache."""
    current_data = DisasterService.get_latest_data()
    if not current_data:
        logger.warning("[PREDICTION API] /train called but no realtime data is available.")
        return {"message": "No realtime data available to learn from."}

    count = guardian_brain.learn(current_data)
    logger.info(f"[PREDICTION API] Manual training triggered — {count} events learned.")
    return {
        "message": "Neural Core updated successfully.",
        "total_events_learned": count,
        "source_events": len(current_data),
    }


@router.post("/forecast", dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
async def forecast_disaster(req: NeuralPredictionRequest, request: Request):
    """AI-powered risk forecast at a specific coordinate."""
    risk = await run_in_threadpool(
        guardian_brain.predict_risk, req.lat, req.lon, req.simulated_energy, 0.5
    )

    alert_level = "NORMAL"
    if risk > 0.5: alert_level = "WARNING"
    if risk > 0.8: alert_level = "CRITICAL"

    logger.info(
        f"[PREDICTION API] AI forecast at ({req.lat}, {req.lon}): "
        f"Risk {risk:.2f} -> {alert_level}"
    )

    return {
        "lat": req.lat,
        "lon": req.lon,
        "risk_score": risk,
        "alert_level": alert_level,
        "model_type": "HistGradientBoosting Time-Series"
    }

@router.get("/global-scan", dependencies=[Depends(require_api_key)])
@limiter.limit("5/minute")
async def global_scan(request: Request):
    """AI-powered risk forecast for major global fault lines."""
    # Các điểm nóng đứt gãy kiến tạo (Ring of Fire, v.v...)
    HOTSPOTS = [
        {"name": "Tokyo, Japan", "lat": 35.6, "lon": 139.6},
        {"name": "California, USA", "lat": 36.7, "lon": -119.4},
        {"name": "Santiago, Chile", "lat": -33.4, "lon": -70.6},
        {"name": "Manila, Philippines", "lat": 14.5, "lon": 120.9},
        {"name": "Jakarta, Indonesia", "lat": -6.2, "lon": 106.8},
        {"name": "Istanbul, Turkey", "lat": 41.0, "lon": 28.9},
        {"name": "Wellington, NZ", "lat": -41.2, "lon": 174.7},
        {"name": "Taiwan", "lat": 23.6, "lon": 120.9},
        {"name": "Mexico City", "lat": 19.4, "lon": -99.1},
        {"name": "Tehran, Iran", "lat": 35.6, "lon": 51.3},
        {"name": "Lima, Peru", "lat": -12.0, "lon": -77.0},
        {"name": "Naples, Italy", "lat": 40.8, "lon": 14.2},
        {"name": "Iceland", "lat": 64.9, "lon": -19.0},
        {"name": "Alaska, USA", "lat": 64.2, "lon": -149.4},
        {"name": "Hawaii, USA", "lat": 19.8, "lon": -155.8},
        {"name": "Sumatra, Indonesia", "lat": 0.5, "lon": 101.5},
        {"name": "Fiji", "lat": -17.7, "lon": 178.0},
        {"name": "Kathmandu, Nepal", "lat": 27.7, "lon": 85.3},
        {"name": "San Francisco, USA", "lat": 37.7, "lon": -122.4},
        {"name": "Hokkaido, Japan", "lat": 43.2, "lon": 142.8}
    ]
    
    # Lấy dữ liệu thiên tai đang xảy ra thực tế từ cache
    live_events = DisasterService.get_latest_data()
    
    results = []
    for spot in HOTSPOTS:
        # Tính năng lượng cục bộ THỰC TẾ dựa trên các thiên tai đang xảy ra gần điểm đó
        local_energy = _calc_local_energy(spot["lat"], spot["lon"], live_events)
        # Dị thường cục bộ: tỉ lệ với mật độ sự kiện xung quanh
        local_anomaly = min(local_energy * 1.2, 1.0)
        
        risk = await run_in_threadpool(
            guardian_brain.predict_risk, spot["lat"], spot["lon"], local_energy, local_anomaly
        )
        alert_level = "NORMAL"
        if risk > 0.5: alert_level = "WARNING"
        if risk > 0.8: alert_level = "CRITICAL"
        
        results.append({
            "name": spot["name"],
            "lat": spot["lat"],
            "lon": spot["lon"],
            "risk_score": round(risk, 3),
            "local_energy": round(local_energy, 3),
            "alert_level": alert_level
        })
        
    logger.info(f"[PREDICTION API] Global scan completed for {len(HOTSPOTS)} regions.")
    
    return {
        "status": "COMPLETED",
        "count": len(results),
        "data": results
    }