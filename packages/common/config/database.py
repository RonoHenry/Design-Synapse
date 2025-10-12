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
        case_sensitive=False,
        extra="ignore",
    )

    # Database type
    database_type: str = Field(default="tidb", pattern="^(postgresql|mysql|tidb)$")

    # Connection settings
    host: str = "localhost"
    port: int = Field(default=4000, ge=1, le=65535)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    database: str = Field(..., min_length=1)

    # Connection pool settings (optimized for TiDB Serverless)
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    pool_timeout: int = Field(default=30, ge=1)
    pool_recycle: int = Field(default=3600, ge=300)
    pool_pre_ping: bool = Field(default=True)

    # Connection timeout and retry settings
    connect_timeout: int = Field(default=10, ge=1, le=60)
    read_timeout: int = Field(default=30, ge=1, le=300)
    write_timeout: int = Field(default=30, ge=1, le=300)

    # SSL/TLS settings (required for TiDB Serverless)
    ssl_mode: str = "prefer"
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_ca: Optional[str] = None
    ssl_verify_cert: bool = Field(default=True)
    ssl_verify_identity: bool = Field(default=True)

    # MySQL/TiDB specific settings
    charset: str = Field(default="utf8mb4")

    # Query settings
    echo: bool = False
    echo_pool: bool = False

    @field_validator("ssl_mode")
    @classmethod
    def validate_ssl_mode(cls, v: str) -> str:
        """Validate SSL mode (PostgreSQL specific)."""
        valid_modes = [
            "disable",
            "allow",
            "prefer",
            "require",
            "verify-ca",
            "verify-full",
        ]
        if v not in valid_modes:
            raise ValueError(f"ssl_mode must be one of: {', '.join(valid_modes)}")
        return v

    @field_validator("database_type")
    @classmethod
    def validate_database_type(cls, v: str) -> str:
        """Validate database type."""
        valid_types = ["postgresql", "mysql", "tidb"]
        if v not in valid_types:
            raise ValueError(f"database_type must be one of: {', '.join(valid_types)}")
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
        """Generate database connection URL for PostgreSQL, MySQL, or TiDB."""
        # Determine driver based on database type
        if self.database_type == "postgresql":
            driver = "postgresql+asyncpg" if async_driver else "postgresql+psycopg2"
        elif self.database_type in ("mysql", "tidb"):
            # TiDB uses MySQL protocol
            driver = "mysql+aiomysql" if async_driver else "mysql+pymysql"
        else:
            raise ValueError(f"Unsupported database_type: {self.database_type}")

        url = f"{driver}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

        # Add parameters based on database type
        params = []

        if self.database_type == "postgresql":
            # PostgreSQL SSL parameters
            if self.ssl_mode != "prefer":
                params.append(f"sslmode={self.ssl_mode}")
            if self.ssl_cert:
                params.append(f"sslcert={self.ssl_cert}")
            if self.ssl_key:
                params.append(f"sslkey={self.ssl_key}")
            if self.ssl_ca:
                params.append(f"sslrootcert={self.ssl_ca}")

        elif self.database_type in ("mysql", "tidb"):
            # MySQL/TiDB parameters
            params.append(f"charset={self.charset}")

            # SSL/TLS configuration for TiDB
            if self.ssl_ca:
                params.append(f"ssl_ca={self.ssl_ca}")
            if self.ssl_verify_cert:
                params.append("ssl_verify_cert=true")
            if self.ssl_verify_identity:
                params.append("ssl_verify_identity=true")

            # Timeout settings
            params.append(f"connect_timeout={self.connect_timeout}")
            params.append(f"read_timeout={self.read_timeout}")
            params.append(f"write_timeout={self.write_timeout}")

        if params:
            url += "?" + "&".join(params)

        return url

    def get_engine_kwargs(self) -> dict:
        """Get SQLAlchemy engine configuration optimized for database type."""
        kwargs = {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
            "echo": self.echo,
            "echo_pool": self.echo_pool,
        }

        # Add TiDB/MySQL specific connection arguments
        if self.database_type in ("mysql", "tidb"):
            connect_args = {}

            # SSL configuration
            if self.ssl_ca:
                import ssl

                connect_args["ssl"] = {
                    "ca": self.ssl_ca,
                    "check_hostname": self.ssl_verify_identity,
                    "verify_mode": ssl.CERT_REQUIRED
                    if self.ssl_verify_cert
                    else ssl.CERT_NONE,
                }

            if connect_args:
                kwargs["connect_args"] = connect_args

        return kwargs

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
