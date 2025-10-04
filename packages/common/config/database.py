"""
Database configuration classes.
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration with connection pooling and validation."""
    
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Connection settings
    host: str = "localhost"
    port: int = Field(default=5432, ge=1, le=65535)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    database: str = Field(..., min_length=1)
    
    # Connection pool settings
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    pool_timeout: int = Field(default=30, ge=1)
    pool_recycle: int = Field(default=3600, ge=300)
    
    # SSL settings
    ssl_mode: str = "prefer"
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_ca: Optional[str] = None
    
    # Query settings
    echo: bool = False
    echo_pool: bool = False
    
    @field_validator("ssl_mode")
    @classmethod
    def validate_ssl_mode(cls, v: str) -> str:
        """Validate SSL mode."""
        valid_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
        if v not in valid_modes:
            raise ValueError(f"ssl_mode must be one of: {', '.join(valid_modes)}")
        return v
    
    @field_validator("pool_size", "max_overflow")
    @classmethod
    def validate_pool_settings(cls, v: int, info) -> int:
        """Validate pool settings are reasonable."""
        if info.field_name == "pool_size" and v < 1:
            raise ValueError("pool_size must be at least 1")
        if info.field_name == "max_overflow" and v < 0:
            raise ValueError("max_overflow must be non-negative")
        return v
    
    def get_connection_url(self, async_driver: bool = False) -> str:
        """Generate database connection URL."""
        driver = "postgresql+asyncpg" if async_driver else "postgresql+psycopg2"
        
        url = f"{driver}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        
        # Add SSL parameters if configured
        params = []
        if self.ssl_mode != "prefer":
            params.append(f"sslmode={self.ssl_mode}")
        if self.ssl_cert:
            params.append(f"sslcert={self.ssl_cert}")
        if self.ssl_key:
            params.append(f"sslkey={self.ssl_key}")
        if self.ssl_ca:
            params.append(f"sslrootcert={self.ssl_ca}")
        
        if params:
            url += "?" + "&".join(params)
        
        return url
    
    def get_engine_kwargs(self) -> dict:
        """Get SQLAlchemy engine configuration."""
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "echo": self.echo,
            "echo_pool": self.echo_pool,
        }
    
    def validate_connection_settings(self) -> None:
        """Validate database connection settings."""
        if not self.username:
            raise ValueError("DB_USERNAME environment variable is required")
        if not self.password:
            raise ValueError("DB_PASSWORD environment variable is required")
        if not self.database:
            raise ValueError("DB_DATABASE environment variable is required")
        
        # Validate pool settings make sense together
        if self.max_overflow > self.pool_size * 2:
            raise ValueError(
                f"max_overflow ({self.max_overflow}) should not be more than "
                f"twice the pool_size ({self.pool_size})"
            )