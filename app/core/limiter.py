from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from fastapi import Request

# Khởi tạo Limiter sử dụng IP của client làm key
limiter = Limiter(key_func=get_remote_address)

def cyber_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom exception handler trả về response chuẩn Cyberpunk khi bị Rate Limit
    """
    return JSONResponse(
        status_code=429,
        content={
            "error": "SYSTEM OVERLOAD. Cooling down core...",
            "alert_level": "WARNING",
            "detail": f"Rate limit exceeded: {exc.detail}"
        }
    )
