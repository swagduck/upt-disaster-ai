from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

from app.core.config import settings
from app.core.logger import get_logger
from app.api.v1.endpoints.router import api_router
from app.api.v1.endpoints import reactor
from app.api.v1.endpoints import prediction
from app.upt_engine.reactor_core import upt_reactor
from app.services.earthquake_service import DisasterService
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter, cyber_rate_limit_handler

logger = get_logger(__name__)

app = FastAPI(
    title="UPT Disaster AI - Guardian System",
    description="Global Monitoring & Reactor Stability Interface",
    version="28.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cyber_rate_limit_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static Files ──────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def read_index():
    return FileResponse("app/static/index.html")


@app.get("/dashboard")
async def read_dashboard():
    return FileResponse("app/static/dashboard.html")


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")
app.include_router(reactor.router, prefix="/api/v1/reactor", tags=["Reactor"])
app.include_router(prediction.router, prefix="/api/v1/predict", tags=["AI Prediction"])


# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info(">>>  UPT GUARDIAN SYSTEM BOOT SEQUENCE INITIATED  <<<")
    logger.info(f"     Host: {settings.HOST}:{settings.PORT}")
    logger.info(f"     DB  : {settings.DB_NAME}")
    logger.info("=" * 60)
    upt_reactor.start_reactor()
    # Chạy tác vụ tải dữ liệu realtime dưới nền để không chặn việc mở cổng (port binding) của Uvicorn trên Render
    asyncio.create_task(DisasterService.fetch_all_realtime())
    logger.info("[MAIN] System fully online.")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("[MAIN] Guardian System shutting down gracefully.")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )