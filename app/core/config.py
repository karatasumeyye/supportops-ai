from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SupportOps AI API"
    app_version: str = "0.1.0"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    database_url: str

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )


# Cache settings so they are loaded once and reused across the app.
@lru_cache
def get_settings() -> Settings:
    return Settings()
