from fastapi import APIRouter, HTTPException
from app.upt_engine.reactor_core import UPTReactorCore
from pydantic import BaseModel

router = APIRouter()

# Khởi tạo Lò phản ứng ảo (Singleton cho phiên chạy này)
reactor = UPTReactorCore()

class ReactorControlRequest(BaseModel):
    entropy_inject: float = 0.1  # Giả lập mức độ hỗn loạn từ ý thức
    enable_ai_safety: bool = True # Bật chế độ bảo vệ Deloris

@router.post("/simulate")
async def simulate_reactor(control: ReactorControlRequest):
    """
    Chạy một chu kỳ mô phỏng lò phản ứng UPT-RC
    """
    try:
        result = reactor.simulate_step(
            entropy_input=control.entropy_inject,
            ai_intervention=control.enable_ai_safety
        )
        
        # Cảnh báo nguy hiểm nếu nhiệt độ quá cao
        if result["core_temp"] > 2000:
            result["alert"] = "CRITICAL: MELTDOWN IMMINENT"
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scram")
async def manual_scram():
    """
    SCRAM: Dừng khẩn cấp bằng cách bơm nhiễu pha cực đại
    """
    reactor.phase_noise = 100.0 # Maximum decoherence
    reactor.neutron_flux = 0.0
    return {"status": "SCRAM_EXECUTED", "message": "Phase Noise set to MAXIMUM. Chain reaction halted."}