from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

from app.core.config import settings
from app.core.database import Database
from app.core.logger import get_logger
from app.api.v1.endpoints.router import api_router
from app.api.v1.endpoints import reactor
from app.api.v1.endpoints import prediction
from app.upt_engine.reactor_core import upt_reactor
from app.upt_engine.deep_core import guardian_brain
from app.services.earthquake_service import DisasterService
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter, cyber_rate_limit_handler

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

logger = get_logger(__name__)


# ── Lifespan (replaces deprecated @app.on_event) ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown lifecycle managed in one place."""
    # ── STARTUP ───────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(">>>  UPT GUARDIAN SYSTEM BOOT SEQUENCE INITIATED  <<<")
    logger.info(f"     Host: {settings.HOST}:{settings.PORT}")
    logger.info(f"     DB  : {settings.DB_NAME}")
    logger.info(f"     CORS: {settings.cors_origins}")
    logger.info("=" * 60)

    # Lazy DB connection (was previously at import time)
    Database.connect()

    upt_reactor.start_reactor()

    # Khởi tạo Caching (In-Memory)
    FastAPICache.init(InMemoryBackend(), prefix="upt-cache")

    # Khởi tạo mô hình AI và huấn luyện từ MongoDB dưới nền
    asyncio.create_task(asyncio.to_thread(guardian_brain.initialize))
    # Chạy tác vụ tải dữ liệu realtime dưới nền
    asyncio.create_task(DisasterService.fetch_all_realtime())

    logger.info("[MAIN] System fully online.")

    yield  # ── App runs here ──

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    logger.info("[MAIN] Guardian System shutting down gracefully.")


app = FastAPI(
    title="UPT Disaster AI - Guardian System",
    description="Global Monitoring & Reactor Stability Interface",
    version="28.2.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cyber_rate_limit_handler)

# ── CORS — reads from settings.cors_origins ───────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )