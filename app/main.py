import os
import asyncio
import logging
from contextlib import asynccontextmanager
# --- SỬA LỖI: Thêm Request vào dòng import này ---
from fastapi import FastAPI, Request 
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# --- Rate Limiting ---
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# --- Background Scheduler ---
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# Import Internal Modules
from app.api.v1.endpoints.router import api_router
from app.api.v1.endpoints import reactor
from app.services.earthquake_service import DisasterService

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UPT_GUARDIAN")

load_dotenv()

# --- 1. SETUP RATE LIMITER ---
limiter = Limiter(key_func=get_remote_address)

# --- 2. SETUP SCHEDULER ---
scheduler = AsyncIOScheduler()

async def scheduled_scan():
    """
    Chạy ngầm mỗi 5 phút. 
    Tự động báo lỗi về Telegram nếu có sự cố (Self-Reporting).
    """
    logger.info("🔄 [SYSTEM] Auto-scanning for threats...")
    try:
        await DisasterService.fetch_all_realtime()
    except Exception as e:
        error_msg = f"⚠️ [SYSTEM FAILURE] Auto-scan error: {str(e)}"
        logger.error(error_msg)
        await DisasterService.send_telegram_alert(error_msg)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    logger.info("🚀 UPT SYSTEM INITIALIZED. Starting Scheduler...")
    
    asyncio.create_task(scheduled_scan())
    
    scheduler.add_job(scheduled_scan, 'interval', seconds=300)
    scheduler.start()
    
    yield # App chạy tại đây
    
    # --- SHUTDOWN ---
    logger.info("🛑 System Shutdown. Stopping Scheduler...")
    scheduler.shutdown()

# Khởi tạo App
app = FastAPI(title="UPT Disaster AI", version="27.8", lifespan=lifespan)

# Gắn Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- 3. CẤU HÌNH CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 4. MOUNT STATIC FILES & ROUTERS ---
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(api_router, prefix="/api/v1")
app.include_router(reactor.router, prefix="/api/v1/reactor", tags=["Reactor"])

# --- 5. HEALTH CHECK ---
@app.get("/health")
def health_check():
    return {
        "status": "online", 
        "guardian": "active", 
        "version": "27.8"
    }

# --- 6. TRANG CHỦ (SỬA LỖI TẠI ĐÂY) ---
@app.get("/")
@limiter.limit("60/minute") 
async def read_index(request: Request): # <-- Dùng trực tiếp Request đã import ở trên
    return FileResponse("app/static/index.html")

# --- ENTRY POINT ---
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)