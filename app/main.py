import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# Import các Router & Services
from app.api.v1.endpoints.router import api_router
from app.api.v1.endpoints import reactor
from app.services.earthquake_service import DisasterService

# Tải biến môi trường
load_dotenv()

# --- BACKGROUND SCHEDULER SETUP ---
# Tạo một trình quản lý tác vụ chạy ngầm
scheduler = AsyncIOScheduler()

async def scheduled_scan():
    """
    Hàm này sẽ chạy ngầm định kỳ mỗi 5 phút (300s).
    Nhiệm vụ: Tự động quét dữ liệu từ USGS/NASA và báo Telegram
    ngay cả khi không có ai đang mở trang web.
    """
    print("🔄 [SYSTEM] Auto-scanning for threats (Background Job)...")
    try:
        # Gọi service quét dữ liệu (đã viết ở các bước trước)
        await DisasterService.fetch_all_realtime()
    except Exception as e:
        print(f"⚠️ Background Scan Failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Hàm này quản lý vòng đời của ứng dụng (Startup & Shutdown).
    """
    # --- STARTUP: Bật Scheduler khi Server khởi động ---
    print("🚀 UPT SYSTEM INITIALIZED. Starting Guardian Scheduler...")
    
    # Thêm job chạy mỗi 300 giây (5 phút)
    scheduler.add_job(scheduled_scan, 'interval', seconds=300)
    scheduler.start()
    
    yield # Ứng dụng chạy tại đây
    
    # --- SHUTDOWN: Tắt Scheduler khi Server dừng ---
    print("🛑 System Shutdown. Stopping Scheduler...")
    scheduler.shutdown()

# Khởi tạo App với lifespan đã cấu hình
app = FastAPI(title="UPT Disaster AI", version="27.5", lifespan=lifespan)

# --- CẤU HÌNH CORS (QUAN TRỌNG CHO RENDER) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Trong Production nên đổi thành domain cụ thể của bạn
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Mount thư mục giao diện (Frontend Static Files)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 2. Include các Router API
# Router cho các tính năng dự báo thiên tai
app.include_router(api_router, prefix="/api/v1")
# Router riêng cho Lò phản ứng & WebSocket
app.include_router(reactor.router, prefix="/api/v1/reactor", tags=["Reactor"])

# 3. Route trang chủ (Load giao diện chính)
@app.get("/")
async def read_index():
    return FileResponse("app/static/index.html")

# 4. Entry Point (Chạy Server)
if __name__ == "__main__":
    import uvicorn
    # Lấy PORT từ biến môi trường (do Render cấp), mặc định là 8000
    port = int(os.environ.get("PORT", 8000))
    # Chạy server Uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)