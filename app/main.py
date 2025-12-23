from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import router as api_router, reactor # Import thêm reactor
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="UPT Disaster AI", version="27.0")

# --- CẤU HÌNH CORS CHO RENDER ---
# Cho phép mọi nguồn (hoặc bạn có thể giới hạn chỉ domain render của bạn)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên đổi thành ["https://ten-du-an.onrender.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Router
app.include_router(api_router, prefix="/api/v1")
# Include riêng router Reactor nếu chưa gộp
app.include_router(reactor.router, prefix="/api/v1/reactor", tags=["Reactor"])

# Mount folder static (Giao diện)
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Local run
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)