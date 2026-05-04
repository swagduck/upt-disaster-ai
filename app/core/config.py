"""
Application configuration via Pydantic BaseSettings.
Reads from environment variables / .env file and validates on startup.

Usage:
    from app.core.config import settings
    print(settings.MONGO_URI)
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """
    All configurable values for UPT Disaster AI.
    Fields without defaults MUST be present in the environment / .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",          # Silently ignore extra keys in .env
    )

    # ── Database ─────────────────────────────────────────────────────────────
    MONGO_URI: Optional[str] = Field(
        default=None,
        description="MongoDB Atlas connection string. App runs without DB if absent.",
    )
    DB_NAME: str = Field(default="upt_guardian", description="MongoDB database name.")

    # ── NASA API ──────────────────────────────────────────────────────────────
    NASA_API_KEY: str = Field(
        default="DEMO_KEY",
        description="NASA API key. Falls back to rate-limited DEMO_KEY.",
    )

    # ── Telegram Alerts ───────────────────────────────────────────────────────
    TELEGRAM_TOKEN: Optional[str] = Field(
        default=None,
        description="Telegram Bot token. Alerts are disabled if absent.",
    )
    TELEGRAM_CHAT_ID: Optional[str] = Field(
        default=None,
        description="Telegram chat ID to receive alerts.",
    )

    # ── Server ────────────────────────────────────────────────────────────────
    HOST: str = Field(default="0.0.0.0", description="Uvicorn bind host.")
    PORT: int = Field(default=8000, description="Uvicorn bind port.")
    DEBUG: bool = Field(default=False, description="Enable hot-reload / debug mode.")


# ── Singleton instance (import this everywhere) ───────────────────────────────
settings = Settings()
