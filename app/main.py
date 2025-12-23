from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse # [IMPORT MỚI]
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

from app.api.v1.endpoints.router import api_router
from app.api.v1.endpoints import reactor
from app.api.v1.endpoints import prediction
from app.upt_engine.reactor_core import upt_reactor
from app.services.earthquake_service import DisasterService

app = FastAPI(
    title="UPT Disaster AI - Guardian System",
    description="Global Monitoring & Reactor Stability Interface",
    version="28.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# [THÊM MỚI] Route trang chủ: Trả về giao diện chính thay vì lỗi 404
@app.get("/")
async def read_index():
    return FileResponse('app/static/index.html')

# Register Routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(reactor.router, prefix="/api/v1/reactor", tags=["Reactor"])
app.include_router(prediction.router, prefix="/api/v1/predict", tags=["AI Prediction"])

@app.on_event("startup")
async def startup_event():
    print(">>> SYSTEM BOOT SEQUENCE INITIATED <<<")
    upt_reactor.start_reactor()
    await DisasterService.fetch_all_realtime()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)