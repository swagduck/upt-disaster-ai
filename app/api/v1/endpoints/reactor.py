from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import asyncio

from app.upt_engine.reactor_core import upt_reactor
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ReactorControlRequest(BaseModel):
    entropy_inject: float = 0.1
    enable_ai_safety: bool = True


@router.post("/simulate")
async def simulate_reactor(control: ReactorControlRequest):
    """Apply a manual external stress to the running reactor."""
    try:
        upt_reactor.update_external_stress(control.entropy_inject)
        logger.info(f"[REACTOR API] Manual stress injected: {control.entropy_inject}")
        return upt_reactor.get_status()
    except Exception as e:
        logger.error(f"[REACTOR API] Simulate endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scram")
async def manual_scram():
    """Trigger emergency reactor shutdown (SCRAM)."""
    logger.critical("[REACTOR API] 🚨 Manual SCRAM initiated by operator.")
    upt_reactor.control_rods = 100.0
    upt_reactor.neutron_flux = 0.0
    upt_reactor.k_eff = 0.0
    upt_reactor.core_temp = 300.0
    return {"status": "SCRAM_EXECUTED", "message": "Manual SCRAM initiated. Reactor Shutdown."}


# ── WebSocket: Real-Time Reactor Status Stream ────────────────────────────────
@router.websocket("/ws/status")
async def websocket_reactor_status(websocket: WebSocket):
    await websocket.accept()
    logger.info("[REACTOR API] WebSocket client connected to reactor stream.")
    try:
        while True:
            data = upt_reactor.get_status()
            await websocket.send_json(data)
            await asyncio.sleep(0.5)   # 2 FPS update rate
    except WebSocketDisconnect:
        logger.info("[REACTOR API] WebSocket client disconnected from reactor stream.")
    except Exception as e:
        logger.error(f"[REACTOR API] WebSocket error: {e}", exc_info=True)
        await websocket.close()


# ── Internal Hook for Earthquake Service ─────────────────────────────────────
@router.post("/inject-event")
async def inject_real_event(magnitude: float):
    """Internal endpoint called when a major earthquake is detected."""
    shock = 0.0
    if magnitude > 6.0:
        shock = 0.5
    if magnitude > 7.5:
        shock = 1.0

    if shock > 0:
        upt_reactor.update_external_stress(shock)
        logger.warning(
            f"[REACTOR API] Seismic event injected — magnitude={magnitude}, shock={shock}"
        )

    return {"status": "SHOCK_RECEIVED", "damage": shock}