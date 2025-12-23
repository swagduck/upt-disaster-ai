from fastapi import APIRouter
from app.services.earthquake_service import DisasterService

api_router = APIRouter()

@api_router.get("/disasters/live")
async def get_live_disasters():
    """
    API nội bộ: Trả về dữ liệu thiên tai đã được Server cache sẵn.
    Nhanh hơn gấp 10 lần so với gọi trực tiếp USGS/NASA.
    """
    data = DisasterService.get_latest_data()
    return {
        "source": "UPT_GUARDIAN_CACHE",
        "count": len(data),
        "data": data
    }