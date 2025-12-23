from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from app.upt_engine.reactor_core import UPTReactorCore
from pydantic import BaseModel
import asyncio
import json

router = APIRouter()

# Singleton Reactor Instance (Dùng chung cho cả app)
reactor = UPTReactorCore()

class ReactorControlRequest(BaseModel):
    entropy_inject: float = 0.1
    enable_ai_safety: bool = True

@router.post("/simulate")
async def simulate_reactor(control: ReactorControlRequest):
    try:
        return reactor.simulate_step(
            entropy_input=control.entropy_inject,
            ai_intervention=control.enable_ai_safety
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scram")
async def manual_scram():
    reactor.phase_noise = 100.0
    reactor.neutron_flux = 0.0
    return {"status": "SCRAM_EXECUTED", "message": "Manual SCRAM initiated."}

# --- NEW: WEBSOCKET REALTIME STREAM ---
@router.websocket("/ws/status")
async def websocket_reactor_status(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Tự động chạy lò phản ứng mỗi 0.5 giây
            # Entropy dao động nhẹ để tạo cảm giác "sống"
            import random
            entropy = random.uniform(0.05, 0.15)
            
            data = reactor.simulate_step(entropy_input=entropy, ai_intervention=True)
            
            # Gửi dữ liệu xuống client
            await websocket.send_json(data)
            
            # FPS: 2 lần/giây
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        print("Client disconnected from Reactor Stream")

# --- NEW: INTERNAL HOOK FOR EARTHQUAKE SERVICE ---
@router.post("/inject-event")
async def inject_real_event(magnitude: float):
    """
    API nội bộ để EarthQuake Service gọi khi có động đất lớn
    """
    shock = 0.0
    if magnitude > 6.0: shock = 0.5
    if magnitude > 7.5: shock = 1.0
    
    reactor.simulate_step(entropy_input=0, ai_intervention=True, external_shock=shock)
    return {"status": "SHOCK_RECEIVED", "damage": shock}