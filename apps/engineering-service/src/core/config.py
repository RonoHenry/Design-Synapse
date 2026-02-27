"""Configuration module for Engineering Service."""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application
    app_name: str = "Engineering Service"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = Field(default="development", alias="ENV")

    # API
    api_v1_prefix: str = "/api/v1"

    # Database (TiDB/MySQL)
    database_url: str = Field(
        default="mysql+asyncmy://root:password@localhost:4000/engineering_service",
        alias="DATABASE_URL",
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_pool_recycle: int = 3600

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/1", alias="REDIS_URL")
    redis_cache_ttl: int = 300  # 5 minutes default cache TTL

    # External Services
    architectural_service_url: str = Field(
        default="http://localhost:8005", alias="ARCHITECTURAL_SERVICE_URL"
    )
    design_service_url: str = Field(
        default="http://localhost:8001", alias="DESIGN_SERVICE_URL"
    )
    knowledge_service_url: str = Field(
        default="http://localhost:8002", alias="KNOWLEDGE_SERVICE_URL"
    )
    project_service_url: str = Field(
        default="http://localhost:8003", alias="PROJECT_SERVICE_URL"
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
    cors_origins: List[str] = ["http://localhost:3000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100

    # Calculation Settings
    calculation_timeout: int = 30  # seconds
    max_calculation_retries: int = 2


# Global settings instance
settings = Settings()
