# app/api/v1/endpoints/prediction.py
from fastapi import APIRouter, HTTPException
from app.schemas.prediction_schema import DisasterPredictionRequest, DisasterPredictionResponse
from app.upt_engine.formulas import UPTMath

router = APIRouter()

@router.post("/predict", response_model=DisasterPredictionResponse)
async def predict_disaster(request: DisasterPredictionRequest):
    """
    API nhận dữ liệu cảm biến và trả về dự báo thiên tai dựa trên UPT.
    """
    try:
        # 1. Tính toán các giá trị trung bình từ mạng lưới sensors
        avg_energy = sum(s.energy_level for s in request.sensors) / len(request.sensors)
        avg_anomaly = sum(s.anomaly_score for s in request.sensors) / len(request.sensors)

        # [cite_start]2. Tính Cộng hưởng mạng lưới (Formula 3 - UPT) [cite: 10]
        # Nếu các sensor cùng có năng lượng cao và bất thường cao => Resonance lớn
        resonance_score = UPTMath.calculate_resonance(request.sensors)

        # [cite_start]3. Tính Xác suất Sụp đổ/Thiên tai (Formula 2 - UPT) [cite: 10]
        # Kết hợp: Bất thường * Năng lượng * Yếu tố địa chất
        prob_index = UPTMath.calculate_collapse_probability(
            avg_anomaly=avg_anomaly,
            avg_energy=avg_energy,
            conditions=request.geo_vulnerability
        )

        # [cite_start]4. Tính độ Ổn định (Formula RC - UPT) [cite: 169]
        # Coi Resonance là lực phá hoại, Geo là độ yếu
        stability_index = UPTMath.calculate_stability(
            destructive_force=resonance_score,
            resilience=request.geo_vulnerability, # Ở đây giả sử geo cao là dễ vỡ
            noise=request.environmental_noise,
            dampening=request.active_dampening
        )

        # 5. Phân loại Cảnh báo (Business Logic)
        alert_level = "NORMAL"
        recommendation = "Tiếp tục theo dõi."

        # Logic ngưỡng (Thresholds) - Cần tinh chỉnh qua thực tế
        if prob_index > 0.7 or stability_index > 0.8:
            alert_level = "CRITICAL"
            recommendation = "KÍCH HOẠT SƠ TÁN NGAY LẬP TỨC. Sụp đổ lượng tử sắp xảy ra."
        elif prob_index > 0.4 or stability_index > 0.5:
            alert_level = "WARNING"
            recommendation = "Cảnh báo các đơn vị cứu hộ. Chuẩn bị phương án B."

        return DisasterPredictionResponse(
            region=request.region_name,
            probability_index=round(prob_index, 4),
            network_resonance=round(resonance_score, 4),
            stability_score=round(stability_index, 4),
            alert_level=alert_level,
            action_recommendation=recommendation
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tính toán UPT: {str(e)}")
    
from app.services.earthquake_service import USGSService # Import file mới tạo

# API Mới: Lấy dữ liệu thật từ USGS
@router.get("/realtime/usgs")
async def get_realtime_prediction():
    # 1. Lấy dữ liệu thật
    real_sensors = USGSService.fetch_live_data()
    
    if not real_sensors:
        return {"message": "Không có dữ liệu động đất mới hoặc lỗi kết nối USGS."}

    # 2. Chuyển đổi sang format của UPT Engine
    # Vì hàm tính toán của chúng ta cần object SensorData, ta làm giả lập nhanh ở đây
    # (Trong production cần convert kỹ hơn)
    
    # Tính trung bình nhanh để đưa ra cảnh báo chung
    avg_energy = sum(s['energy_level'] for s in real_sensors) / len(real_sensors)
    avg_anomaly = sum(s['anomaly_score'] for s in real_sensors) / len(real_sensors)
    
    # 3. Chạy công thức UPT (Sụp đổ & Cộng hưởng) [cite: 10, 29]
    prob_index = UPTMath.calculate_collapse_probability(avg_anomaly, avg_energy, conditions=0.5)
    resonance = UPTMath.calculate_resonance([
        # Mock object cho hàm tính toán
        type('obj', (object,), s) for s in real_sensors 
    ])
    
    stability = UPTMath.calculate_stability(resonance, 0.5, 0.1, 0.0)
    
    # 4. Logic Cảnh báo
    alert = "NORMAL"
    if prob_index > 0.4: alert = "WARNING"
    if prob_index > 0.7: alert = "CRITICAL"

    return {
        "source": "USGS Live Data",
        "detected_events": len(real_sensors),
        "latest_event": real_sensors[0]['place'],
        "upt_metrics": {
            "probability_index": prob_index,
            "network_resonance": resonance,
            "stability_score": stability,
            "alert_level": alert
        },
        "raw_sensors": real_sensors
    }