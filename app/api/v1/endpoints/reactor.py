from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import asyncio
import random

# [QUAN TRỌNG] Import instance đang chạy từ core, KHÔNG tạo mới
from app.upt_engine.reactor_core import upt_reactor

router = APIRouter()

class ReactorControlRequest(BaseModel):
    entropy_inject: float = 0.1
    enable_ai_safety: bool = True

@router.post("/simulate")
async def simulate_reactor(control: ReactorControlRequest):
    """
    API để client tác động thủ công vào lò phản ứng
    """
    try:
        # Thay vì simulate_step, ta bơm entropy vào lò đang chạy
        upt_reactor.update_external_stress(control.entropy_inject)
        return upt_reactor.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scram")
async def manual_scram():
    """
    Kích hoạt quy trình dập lò khẩn cấp (SCRAM)
    """
    # Can thiệp trực tiếp vào các chỉ số lõi
    upt_reactor.control_rods = 100.0  # Hạ hết thanh điều khiển
    upt_reactor.neutron_flux = 0.0    # Cắt dòng neutron
    upt_reactor.k_eff = 0.0           # Triệt tiêu phản ứng chuỗi
    upt_reactor.core_temp = 300.0     # Reset nhiệt độ về mức thường
    
    return {"status": "SCRAM_EXECUTED", "message": "Manual SCRAM initiated. Reactor Shutdown."}

# --- WEBSOCKET REALTIME STREAM ---
@router.websocket("/ws/status")
async def websocket_reactor_status(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Lấy trạng thái hiện tại từ lò phản ứng (đang chạy ngầm)
            data = upt_reactor.get_status()
            
            # Gửi xuống client
            await websocket.send_json(data)
            
            # Tốc độ làm mới: 2 FPS (0.5s)
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        print("Client disconnected from Reactor Stream")
    except Exception as e:
        print(f"WS Error: {e}")
        await websocket.close()

# --- INTERNAL HOOK FOR EARTHQUAKE SERVICE ---
@router.post("/inject-event")
async def inject_real_event(magnitude: float):
    """
    API nội bộ để EarthQuake Service gọi khi có động đất lớn
    """
    shock = 0.0
    if magnitude > 6.0: shock = 0.5
    if magnitude > 7.5: shock = 1.0
    
    if shock > 0:
        upt_reactor.update_external_stress(shock)
        
    return {"status": "SHOCK_RECEIVED", "damage": shock}