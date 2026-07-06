from fastapi import APIRouter, Depends, Request
import math
import random
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from fastapi_cache.decorator import cache
from fastapi import BackgroundTasks
from typing import List, Optional

from app.services.earthquake_service import DisasterService
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




@router.get("/status")
@cache(expire=60)
async def get_ai_status():
    """Return the current state of the Guardian AI brain."""
    return {
        "status": "ONLINE" if guardian_brain.is_trained else "INITIALIZING",
        "buffer_size": len(guardian_brain.realtime_buffer),
        "model_type": "Deep Learning LSTM (TensorFlow/Keras)",
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
        "model_type": "LSTM Neural Network Time-Series"
    }

def _generate_dynamic_grid():
    """Tạo ra lưới tọa độ động từ các cụm đứt gãy do AI DBSCAN phát hiện."""
    hotspots = guardian_brain.dynamic_hotspots
    
    # Fallback nếu AI chưa quét xong
    if not hotspots:
        base_faults = [
            {"lat_range": (30, 45), "lon_range": (130, 145), "base_risk": 0.22, "name": "Japan Trench"},
            {"lat_range": (32, 40), "lon_range": (-125, -115), "base_risk": 0.18, "name": "San Andreas Fault"},
        ]
        grid = []
        for fault in base_faults:
            for _ in range(5):
                lat = random.uniform(fault["lat_range"][0], fault["lat_range"][1])
                lon = random.uniform(fault["lon_range"][0], fault["lon_range"][1])
                grid.append({
                    "name": f"{fault['name']} Region",
                    "lat": round(lat, 3),
                    "lon": round(lon, 3),
                    "base_risk": fault["base_risk"]
                })
        return grid

    grid = []
    for spot in hotspots:
        # Generate random points around the centroid
        for _ in range(5):
            lat = spot["lat"] + random.uniform(-2.0, 2.0)
            lon = spot["lon"] + random.uniform(-2.0, 2.0)
            grid.append({
                "name": spot["name"],
                "lat": round(lat, 3),
                "lon": round(lon, 3),
                "base_risk": spot["base_risk"]
            })
    return grid

def _get_region_name(lat, lon):
    hotspots = guardian_brain.dynamic_hotspots
    if not hotspots:
        return "Deep Ocean/Unknown"
        
    closest_name = "Deep Ocean/Unknown"
    min_dist = 9999
    for spot in hotspots:
        dist = math.sqrt((lat - spot["lat"])**2 + (lon - spot["lon"])**2)
        if dist < min_dist:
            min_dist = dist
            closest_name = spot["name"]
    return closest_name if min_dist < 40 else "Deep Ocean/Unknown"

@router.get("/global-scan")
@limiter.limit("5/minute")
async def global_scan(request: Request):
    """Spatio-Temporal AI-powered risk forecast for dynamic global grid."""
    live_events = DisasterService.get_latest_data()
    results = []
    
    # 1. AI PREDICTED HAZARDS (SPATIAL LSTMs)
    next_hazards = await run_in_threadpool(guardian_brain.predict_next_hazards)
    for hazard in next_hazards:
        # Tự động gán rủi ro cực đại cho tọa độ AI dự đoán
        local_energy = _calc_local_energy(hazard["lat"], hazard["lon"], live_events)
        region = _get_region_name(hazard["lat"], hazard["lon"])
        
        hazard_type_name = "EPICENTER"
        mag_str = f"M{hazard['mag']}"
        if hazard["type"] == "STORM":
            hazard_type_name = "TYPHOON"
            cat = max(1, min(5, int(hazard['mag'] / 2)))
            mag_str = f"Cat {cat}"
        elif hazard["type"] == "WILDFIRE":
            hazard_type_name = "WILDFIRE"
            lvl = max(1, min(5, int(hazard['mag'] / 2)))
            mag_str = f"Level {lvl}"
        
        # Calculate real probability
        local_anomaly = min(local_energy * 1.5, 1.0)
        base_prob = await run_in_threadpool(guardian_brain.predict_risk, hazard["lat"], hazard["lon"], local_energy, local_anomaly)
        
        # Factor in Severity
        if hazard["type"] == "EARTHQUAKE":
            severity = min(hazard["mag"] / 7.0, 1.0)
        else:
            severity = min(hazard["mag"] / 10.0, 1.0)
            
        final_risk = (base_prob * 0.4) + (severity * 0.6)
        
        alert_lvl = "NORMAL"
        if final_risk > 0.75: alert_lvl = "CRITICAL"
        elif final_risk > 0.45: alert_lvl = "WARNING"

        results.append({
            "name": f"AI PREDICTED {hazard_type_name}: {region} ({mag_str} EXPECTED)",
            "lat": hazard["lat"],
            "lon": hazard["lon"],
            "depth": hazard.get("depth", 10.0),
            "hazard_type": hazard["type"],
            "risk_score": final_risk,
            "local_energy": round(local_energy, 3),
            "base_risk": float(base_prob),
            "alert_level": alert_lvl
        })
        logger.info(f"[PREDICTION API] Spatial LSTM predicted {hazard_type_name} at {hazard['lat']}, {hazard['lon']} with Risk: {final_risk:.2f}")

    # 2. DYNAMIC GRID SCAN (TEMPORAL LSTM)
    dynamic_hotspots = _generate_dynamic_grid()
    
    for spot in dynamic_hotspots:
        local_energy = _calc_local_energy(spot["lat"], spot["lon"], live_events)
        blended_energy = local_energy * 0.50 + spot["base_risk"] * 0.50
        local_anomaly = min(blended_energy * 1.2, 1.0)

        risk = await run_in_threadpool(
            guardian_brain.predict_risk, spot["lat"], spot["lon"], blended_energy, local_anomaly
        )

        micro_noise = random.uniform(0.004, 0.018)
        risk = min(risk + micro_noise, 1.0)

        alert_level = "NORMAL"
        if risk > 0.5: alert_level = "WARNING"
        if risk > 0.8: alert_level = "CRITICAL"

        results.append({
            "name": spot["name"],
            "lat": spot["lat"],
            "lon": spot["lon"],
            "risk_score": round(risk, 3),
            "local_energy": round(local_energy, 3),
            "base_risk": spot["base_risk"],
            "alert_level": alert_level
        })

    # Chỉ lấy Top 15 khu vực rủi ro cao nhất để hiển thị
    results = sorted(results, key=lambda x: x["risk_score"], reverse=True)[:15]

    logger.info(f"[PREDICTION API] Global scan completed. Generated {len(dynamic_hotspots)} dynamic zones, returning Top 15.")

    return {
        "status": "COMPLETED",
        "count": len(results),
        "data": results
    }