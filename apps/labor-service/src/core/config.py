"""
Labor Service Configuration Management

Handles environment variables, database settings, and service configuration
for the Labor Services Marketplace.
"""

from typing import Optional, List
from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings
from functools import lru_cache


class LaborServiceSettings(BaseSettings):
    """Labor Service configuration settings"""
    
    # Application settings
    app_name: str = "Labor Services Marketplace"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = Field(default="development", alias="ENVIRONMENT")
    
    # Server settings
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8006, alias="PORT")
    
    # Database settings
    database_url: str = Field(alias="DATABASE_URL")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")
    
    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    
    # Authentication settings
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, alias="JWT_EXPIRATION_HOURS")
    
    # External service URLs
    user_service_url: str = Field(default="http://localhost:8001", alias="USER_SERVICE_URL")
    project_service_url: str = Field(default="http://localhost:8002", alias="PROJECT_SERVICE_URL")
    vendor_service_url: str = Field(default="http://localhost:8005", alias="VENDOR_SERVICE_URL")
    
    # Payment gateway settings
    stripe_secret_key: Optional[str] = Field(default=None, alias="STRIPE_SECRET_KEY")
    stripe_publishable_key: Optional[str] = Field(default=None, alias="STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: Optional[str] = Field(default=None, alias="STRIPE_WEBHOOK_SECRET")
    
    # Geolocation settings
    google_maps_api_key: Optional[str] = Field(default=None, alias="GOOGLE_MAPS_API_KEY")
    mapbox_access_token: Optional[str] = Field(default=None, alias="MAPBOX_ACCESS_TOKEN")
    
    # Notification settings
    sendgrid_api_key: Optional[str] = Field(default=None, alias="SENDGRID_API_KEY")
    twilio_account_sid: Optional[str] = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    
    # File storage settings
    aws_access_key_id: Optional[str] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    s3_bucket_name: Optional[str] = Field(default=None, alias="S3_BUCKET_NAME")
    
    # Search settings
    elasticsearch_url: Optional[str] = Field(default=None, alias="ELASTICSEARCH_URL")
    
    # Background check integration
    checkr_api_key: Optional[str] = Field(default=None, alias="CHECKR_API_KEY")
    
    # Logging settings
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    
    # CORS settings
    cors_origins: List[str] = Field(default=["*"], alias="CORS_ORIGINS")
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")
    
    # Matching algorithm settings
    matching_radius_miles: int = Field(default=50, alias="MATCHING_RADIUS_MILES")
    max_providers_per_match: int = Field(default=20, alias="MAX_PROVIDERS_PER_MATCH")
    
    # Business settings
    platform_fee_percentage: float = Field(default=5.0, alias="PLATFORM_FEE_PERCENTAGE")
    escrow_hold_days: int = Field(default=7, alias="ESCROW_HOLD_DAYS")
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @field_validator('platform_fee_percentage')
    @classmethod
    def validate_platform_fee(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Platform fee must be between 0 and 100 percent')
        return v
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra='ignore'  # Ignore extra environment variables not defined in the model
    )


@lru_cache()
def get_settings() -> LaborServiceSettings:
    """Get cached application settings"""
    return LaborServiceSettings()


# Database configuration
def get_database_url() -> str:
    """Get database URL with proper formatting"""
    settings = get_settings()
    return settings.database_url


def get_redis_url() -> str:
    """Get Redis URL"""
    settings = get_settings()
    return settings.redis_url


# Service URLs
def get_user_service_url() -> str:
    """Get User Service URL"""
    settings = get_settings()
    return settings.user_service_url


def get_project_service_url() -> str:
    """Get Project Service URL"""
    settings = get_settings()
    return settings.project_service_url


def get_vendor_service_url() -> str:
    """Get Vendor Service URL"""
    settings = get_settings()
    return settings.vendor_service_url