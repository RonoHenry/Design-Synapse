"""Configuration module using common packages."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application
    app_name: str = "Architectural Service"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = Field(default="development", alias="ENV")

    # API
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = Field(
        default="mysql+asyncmy://root:password@localhost:4000/architectural_service",
        alias="DATABASE_URL",
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_pool_recycle: int = 3600

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_cache_ttl: int = 3600

    # External Services
    design_service_url: str = Field(
        default="http://localhost:8001", alias="DESIGN_SERVICE_URL"
    )
    knowledge_service_url: str = Field(
        default="http://localhost:8002", alias="KNOWLEDGE_SERVICE_URL"
    )
    project_service_url: str = Field(
        default="http://localhost:8003", alias="PROJECT_SERVICE_URL"
    )
    vendor_service_url: str = Field(
        default="http://localhost:8004", alias="VENDOR_SERVICE_URL"
    )

    # Circuit Breaker
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 60
    circuit_breaker_half_open_timeout: int = 30

    # Retry
    retry_max_attempts: int = 3
    retry_backoff_factor: float = 2.0
    retry_max_delay: int = 60

    # Authentication
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production", alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100

    # File Upload
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_drawing_types: list[str] = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "application/dwg",
        "application/dxf",
    ]

    # Storage
    storage_path: str = Field(default="./storage", alias="STORAGE_PATH")

    # Collaboration
    websocket_heartbeat_interval: int = 30
    websocket_timeout: int = 300


# Global settings instance
settings = Settings()
