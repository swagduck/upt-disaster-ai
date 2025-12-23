import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from app.api.v1.endpoints.router import api_router
from app.api.v1.endpoints import reactor
from app.services.earthquake_service import DisasterService

load_dotenv()

scheduler = AsyncIOScheduler()

async def scheduled_scan():
    """
    Chạy ngầm mỗi 5 phút. Tự động báo lỗi về Telegram nếu có sự cố.
    """
    print("🔄 [SYSTEM] Auto-scanning for threats...")
    try:
        await DisasterService.fetch_all_realtime()
    except Exception as e:
        # --- TÍNH NĂNG MỚI: TỰ BÁO LỖI ---
        error_msg = f"⚠️ [SYSTEM FAILURE] Auto-scan error: {str(e)}"
        print(error_msg)
        await DisasterService.send_telegram_alert(error_msg)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 UPT SYSTEM INITIALIZED. Starting Scheduler...")
    # Quét ngay lần đầu tiên khi bật server để không phải chờ 5 phút
    asyncio.create_task(scheduled_scan())
    
    scheduler.add_job(scheduled_scan, 'interval', seconds=300)
    scheduler.start()
    yield
    print("🛑 System Shutdown. Stopping Scheduler...")
    scheduler.shutdown()

app = FastAPI(title="UPT Disaster AI", version="27.6", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(api_router, prefix="/api/v1")
app.include_router(reactor.router, prefix="/api/v1/reactor", tags=["Reactor"])

# --- TÍNH NĂNG MỚI: HEALTH CHECK ---
@app.get("/health")
def health_check():
    return {"status": "ok", "guardian": "active"}

@app.get("/")
async def read_index():
    return FileResponse("app/static/index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)