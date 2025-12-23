from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# --- SỬA LỖI IMPORT Ở ĐÂY ---
# Import đúng biến 'api_router' từ file router.py
from app.api.v1.endpoints.router import api_router 
# Import module reactor riêng
from app.api.v1.endpoints import reactor

load_dotenv()

app = FastAPI(title="UPT Disaster AI", version="27.0")

# --- CẤU HÌNH CORS CHO RENDER ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production nên đổi thành domain thật của bạn
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Mount thư mục static
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 2. Include API Router (Disaster Prediction)
app.include_router(api_router, prefix="/api/v1")

# 3. Include API Router (Reactor & Websocket)
# Reactor nằm trong module riêng nên include riêng
app.include_router(reactor.router, prefix="/api/v1/reactor", tags=["Reactor"])

# 4. Trang chủ
from fastapi.responses import FileResponse

@app.get("/")
async def read_index():
    return FileResponse("app/static/index.html")

if __name__ == "__main__":
    import uvicorn
    # Lấy PORT từ biến môi trường (Render tự cấp), mặc định là 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)