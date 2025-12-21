# app/schemas/prediction_schema.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

# Model cho dữ liệu từ 1 trạm cảm biến
class SensorData(BaseModel):
    station_id: str
    energy_level: float = Field(..., ge=0.0, le=1.0, description="Năng lượng đo được (E) từ 0-1")
    anomaly_score: float = Field(..., ge=0.0, le=1.0, description="Chỉ số bất thường (A) từ 0-1")
    location_weight: float = Field(1.0, description="Trọng số vị trí (quan trọng hay không)")

# Model cho Request gửi lên (Input)
class DisasterPredictionRequest(BaseModel):
    region_name: str
    sensors: List[SensorData]
    geo_vulnerability: float = Field(..., ge=0.0, le=1.0, description="Độ yếu địa chất (C_geo)")
    environmental_noise: float = Field(0.1, ge=0.0, description="Độ nhiễu môi trường (tau_noise)")
    active_dampening: float = Field(0.0, ge=0.0, description="Biện pháp can thiệp hiện tại (AI_damp)")

    @field_validator('sensors')
    def check_sensors_list(cls, v):
        if not v:
            raise ValueError('Cần ít nhất dữ liệu từ 1 trạm cảm biến')
        return v

# Model cho Response trả về (Output)
class DisasterPredictionResponse(BaseModel):
    region: str
    probability_index: float  # P(phi)
    network_resonance: float  # R(t)
    stability_score: float    # k_eff
    alert_level: str          # NORMAL, WARNING, CRITICAL
    action_recommendation: str