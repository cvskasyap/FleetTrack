from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str | None = None
    mongodb_uri: str | None = None
    mongodb_database: str = "fleettrack"
    mongodb_collection: str = "tracking_events"
    database_connect_timeout: int = 3
    mongodb_connect_timeout_ms: int = 3000
    session_cookie_secure: bool = False
    session_lifetime_seconds: int = 28800
    login_failure_limit: int = 5
    login_ip_failure_limit: int = 20
    login_failure_window_seconds: int = 900

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    @model_validator(mode="after")
    def require_secure_production_cookies(self) -> "Settings":
        if self.app_env.lower() in {"production", "prod"} and not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be enabled in production.")
        if self.session_lifetime_seconds < 60:
            raise ValueError("SESSION_LIFETIME_SECONDS must be at least 60 seconds.")
        if self.login_failure_limit < 1 or self.login_ip_failure_limit < 1:
            raise ValueError("Login failure limits must be positive.")
        if self.login_failure_window_seconds < 60:
            raise ValueError("LOGIN_FAILURE_WINDOW_SECONDS must be at least 60 seconds.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
