from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.v1.endpoints.router import api_router

app = FastAPI(title="UPT Disaster AI")

# 1. Mount thư mục static (để nhận diện file css/js/html)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 2. Include API Router
app.include_router(api_router, prefix="/api/v1")

# 3. Trang chủ hiển thị giao diện Map
@app.get("/")
async def read_index():
    return FileResponse("app/static/index.html")