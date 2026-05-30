from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Required — must be provided via .env
    DATABASE_URL: str
    REDIS_URL: str
    GEMINI_API_KEY: str

    # Optional with sane defaults
    APP_ENV: str = "production"

    # CORS — comma-separated list of allowed origins.
    # Leave blank to allow all (dev only). In production set explicitly.
    # Example: ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
    ALLOWED_ORIGINS: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
