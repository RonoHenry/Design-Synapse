"""Configuration data models."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DatabaseConfig(BaseModel):
    """Database configuration model."""

    model_config = ConfigDict(from_attributes=True)

    host: str = Field(..., description="Database host")
    port: int = Field(..., description="Database port", ge=1, le=65535)
    name: str = Field(..., description="Database name")
    user: str = Field(..., description="Database user")
    password: Optional[str] = Field(None, description="Database password")

    @field_validator("port")
    @classmethod
    def validate_port(cls, v):
        if not isinstance(v, int) or v < 1 or v > 65535:
            raise ValueError("Port must be an integer between 1 and 65535")
        return v


class RedisConfig(BaseModel):
    """Redis configuration model."""

    model_config = ConfigDict(from_attributes=True)

    host: str = Field(..., description="Redis host")
    port: int = Field(..., description="Redis port", ge=1, le=65535)
    db: int = Field(0, description="Redis database number", ge=0)
    password: Optional[str] = Field(None, description="Redis password")


class APIConfig(BaseModel):
    """API configuration model."""

    model_config = ConfigDict(from_attributes=True)

    host: str = Field("0.0.0.0", description="API host")
    port: int = Field(8000, description="API port", ge=1, le=65535)
    debug: bool = Field(False, description="Debug mode")
    secret_key: Optional[str] = Field(None, description="API secret key")


class ConfigSchema(BaseModel):
    """Main configuration schema combining all config sections."""

    model_config = ConfigDict(from_attributes=True)

    database: DatabaseConfig
    redis: Optional[RedisConfig] = None
    api: Optional[APIConfig] = None
