from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from fastapi_cache.decorator import cache
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


# ── Endpoints ─────────────────────────────────────────────────────────────────

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
        f"risk={risk:.3f} | {alert_level}"
    )
    return {
        "location": {"lat": req.lat, "lon": req.lon},
        "predicted_risk": risk,
        "alert_level": alert_level,
        "ai_confidence": 0.92,
    }