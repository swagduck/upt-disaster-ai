"""
API key authentication dependency for protecting sensitive endpoints.

Usage:
    from app.core.security import require_api_key

    @router.post("/dangerous-action")
    async def dangerous(api_key: str = Depends(require_api_key)):
        ...
"""
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# Header name clients must send: X-API-Key: <secret>
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str:
    """
    FastAPI dependency that enforces API-key auth on sensitive endpoints.

    Behaviour:
      • If API_SECRET_KEY is NOT configured → allow all requests (local dev).
      • If API_SECRET_KEY IS configured → the request must include a valid
        X-API-Key header, otherwise a 403 is returned.
    """
    # Dev mode: no key configured → skip auth
    if not settings.API_SECRET_KEY:
        return "dev-mode"

    if not api_key or api_key != settings.API_SECRET_KEY:
        logger.warning("[SECURITY] ⛔ Unauthorized access attempt blocked.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ACCESS DENIED. Invalid or missing X-API-Key.",
        )

    return api_key
