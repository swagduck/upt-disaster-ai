from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.database import Database
from app.core.logger import get_logger
from app.api.v1.endpoints.router import api_router
from app.api.v1.endpoints import reactor
from app.api.v1.endpoints import prediction
from upt_guardian.reactor_core import upt_reactor
from upt_guardian.deep_core import guardian_brain
from app.services.earthquake_service import DisasterService
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter, cyber_rate_limit_handler

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

logger = get_logger(__name__)

# ── Background job: fetch real-time data & retrain AI ────────────────────────
async def _scheduled_fetch():
    """Tự động chạy mỗi 5 phút: fetch USGS/NASA → cập nhật AI buffer."""
    logger.info("[SCHEDULER] ⏱ Auto-fetch triggered.")
    try:
        await DisasterService.fetch_all_realtime()
        logger.info("[SCHEDULER] ✅ Data refreshed successfully.")
    except Exception as e:
        logger.error(f"[SCHEDULER] ❌ Auto-fetch failed: {e}")
async def _scheduled_nightly_batch():
    """Tự động chạy vào 12h đêm: Học lại toàn bộ dữ liệu lịch sử và quét lại Hotspots."""
    logger.info("[SCHEDULER] 🌙 Bắt đầu tiến trình Nightly Batch Training & Hotspot Scan...")
    try:
        await asyncio.to_thread(guardian_brain.train_from_memory)
        logger.info("[SCHEDULER] ✅ Nightly Batch hoàn tất. Não bộ đã được làm mới!")
    except Exception as e:
        logger.error(f"[SCHEDULER] ❌ Nightly Batch thất bại: {e}")

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

    # Lần fetch đầu tiên ngay khi boot
    asyncio.create_task(DisasterService.fetch_all_realtime())

    # Khởi tạo mô hình AI
    # Pass MongoDB data explicitly to decouple core from app DB
    logger.info("[STARTUP] Loading historical data for AI training...")
    try:
        col = Database.get_collection("raw_logs")
        logs = list(col.find().sort("timestamp", -1).limit(3000)) if col is not None else []
        logs.reverse()
        guardian_brain.initialize(logs)
    except Exception as e:
        logger.error(f"[STARTUP] Error loading data for AI: {e}")
        guardian_brain.initialize([])

    # ── Kích hoạt APScheduler: tự động fetch mỗi 5 phút ──────────────────────
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _scheduled_fetch,
        trigger="interval",
        minutes=5,
        id="disaster_fetch",
        replace_existing=True,
        max_instances=1,          # Không chạy chồng nhau nếu bị chậm
        misfire_grace_time=60,    # Bỏ qua nếu trễ > 60 giây
    )
    scheduler.add_job(
        _scheduled_nightly_batch,
        trigger="cron",
        hour=0,
        minute=0,
        id="nightly_batch",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[SCHEDULER] ✅ APScheduler started — auto-fetch every 5 mins & nightly batch at 00:00.")

    logger.info("[MAIN] System fully online.")

    yield  # ── App runs here ──

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    scheduler.shutdown(wait=False)
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

@app.get("/service-worker.js")
async def read_service_worker():
    return FileResponse("app/static/service-worker.js", media_type="application/javascript")

@app.get("/manifest.json")
async def read_manifest():
    return FileResponse("app/static/manifest.json", media_type="application/manifest+json")
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