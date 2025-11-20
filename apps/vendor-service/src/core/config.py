"""
Vendor Service Configuration.

This module provides configuration management for the Vendor Service using
the unified configuration system with proper environment variable validation.
"""

import os
import sys
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Add the packages directory to the Python path for shared config access
packages_path = Path(__file__).parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.config import BaseServiceConfig, DatabaseConfig, Environment


class VendorSettings(BaseSettings):
    """Vendor-specific configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="VENDOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Vendor limits
    max_products_per_vendor: int = Field(default=1000, ge=1, le=10000)
    max_vendor_name_length: int = Field(default=255, ge=10, le=500)
    max_vendor_description_length: int = Field(default=5000, ge=100, le=50000)

    # Vendor verification
    require_vendor_verification: bool = Field(default=True)
    verification_document_types: str = Field(
        default="business_license,tax_id,insurance"
    )

    # Vendor statuses
    allowed_statuses: str = Field(default="pending,verified,suspended,inactive")

    @field_validator("allowed_statuses")
    @classmethod
    def validate_allowed_statuses(cls, v: str) -> str:
        """Validate vendor statuses."""
        if not v or not v.strip():
            raise ValueError("allowed_statuses cannot be empty")

        statuses = [s.strip().lower() for s in v.split(",")]

        # Ensure required statuses are present
        required_statuses = {"pending", "verified"}
        for status in required_statuses:
            if status not in statuses:
                raise ValueError(
                    f"Required status '{status}' is missing from allowed_statuses"
                )

        return v

    def get_allowed_statuses_list(self) -> List[str]:
        """Get list of allowed vendor statuses."""
        return [s.strip().lower() for s in self.allowed_statuses.split(",")]

    def get_verification_document_types_list(self) -> List[str]:
        """Get list of verification document types."""
        return [d.strip().lower() for d in self.verification_document_types.split(",")]


class ProductSettings(BaseSettings):
    """Product catalog configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="PRODUCT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Product limits
    max_product_name_length: int = Field(default=255, ge=10, le=500)
    max_product_description_length: int = Field(default=10000, ge=100, le=100000)
    max_images_per_product: int = Field(default=10, ge=1, le=50)
    max_variants_per_product: int = Field(default=50, ge=1, le=200)

    # Product categories
    allowed_categories: str = Field(default="materials,tools,equipment,services")

    # Inventory settings
    enable_inventory_tracking: bool = Field(default=True)
    low_stock_threshold: int = Field(default=10, ge=0, le=1000)

    @field_validator("allowed_categories")
    @classmethod
    def validate_allowed_categories(cls, v: str) -> str:
        """Validate product categories."""
        if not v or not v.strip():
            raise ValueError("allowed_categories cannot be empty")
        return v

    def get_allowed_categories_list(self) -> List[str]:
        """Get list of allowed product categories."""
        return [c.strip().lower() for c in self.allowed_categories.split(",")]


class OrderSettings(BaseSettings):
    """Order processing configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="ORDER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Order limits
    max_items_per_order: int = Field(default=100, ge=1, le=500)
    max_order_value: float = Field(default=1000000.0, ge=0.0)

    # Order statuses
    allowed_statuses: str = Field(
        default="pending,confirmed,processing,shipped,delivered,cancelled"
    )

    # Payment settings
    payment_timeout_minutes: int = Field(default=30, ge=5, le=1440)
    enable_partial_payments: bool = Field(default=False)

    @field_validator("allowed_statuses")
    @classmethod
    def validate_allowed_statuses(cls, v: str) -> str:
        """Validate order statuses."""
        if not v or not v.strip():
            raise ValueError("allowed_statuses cannot be empty")

        statuses = [s.strip().lower() for s in v.split(",")]

        # Ensure required statuses are present
        required_statuses = {"pending", "confirmed", "delivered", "cancelled"}
        for status in required_statuses:
            if status not in statuses:
                raise ValueError(
                    f"Required status '{status}' is missing from allowed_statuses"
                )

        return v

    def get_allowed_statuses_list(self) -> List[str]:
        """Get list of allowed order statuses."""
        return [s.strip().lower() for s in self.allowed_statuses.split(",")]


class JWTSettings(BaseSettings):
    """JWT configuration for vendor service."""

    model_config = SettingsConfigDict(
        env_prefix="JWT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    secret_key: str = Field(..., min_length=32)
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)

    @field_validator("algorithm")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm."""
        allowed_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in allowed_algorithms:
            raise ValueError(
                f"algorithm must be one of: {', '.join(allowed_algorithms)}"
            )
        return v


class VendorServiceSettings:
    """Vendor Service configuration settings."""

    def __init__(self):
        # Initialize shared configurations
        self.base = BaseServiceConfig(
            service_name="vendor-service", service_version="1.0.0", port=8006
        )
        self.database = DatabaseConfig()
        self.jwt = JWTSettings()
        self.vendor = VendorSettings()
        self.product = ProductSettings()
        self.order = OrderSettings()

        # Service-specific settings
        self.enable_reviews: bool = (
            os.getenv("ENABLE_REVIEWS", "true").lower() == "true"
        )
        self.enable_staging: bool = (
            os.getenv("ENABLE_STAGING", "true").lower() == "true"
        )

        # Search settings
        self.enable_elasticsearch: bool = (
            os.getenv("ENABLE_ELASTICSEARCH", "false").lower() == "true"
        )
        self.search_results_per_page: int = int(
            os.getenv("SEARCH_RESULTS_PER_PAGE", "20")
        )

        # File storage settings
        self.max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
        self.allowed_file_types: List[str] = os.getenv(
            "ALLOWED_FILE_TYPES", "jpg,jpeg,png,pdf,glb,gltf"
        ).split(",")

        # API rate limiting
        self.rate_limit_requests_per_minute: int = int(
            os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120")
        )
        self.rate_limit_burst: int = int(os.getenv("RATE_LIMIT_BURST", "30"))

        # CORS settings
        self.allowed_origins: List[str] = os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:3000"
        ).split(",")

        # Validate configuration
        self._validate_vendor_service_config()

    # Proxy properties for easy access to base configuration
    @property
    def service_name(self) -> str:
        return self.base.service_name

    @property
    def port(self) -> int:
        return self.base.port

    @property
    def environment(self) -> Environment:
        return self.base.environment

    @property
    def debug(self) -> bool:
        return self.base.debug

    @property
    def log_level(self) -> str:
        return self.base.log_level

    def is_development(self) -> bool:
        return self.base.is_development()

    def is_testing(self) -> bool:
        return self.base.is_testing()

    def is_production(self) -> bool:
        return self.base.is_production()

    def _validate_vendor_service_config(self) -> None:
        """Validate vendor service specific configuration."""
        # Validate base configuration
        self.base.validate_required_settings()

        # Validate database configuration
        self.database.validate_connection_settings()

        # Validate service specific settings
        if self.max_file_size_mb <= 0:
            raise ValueError("MAX_FILE_SIZE_MB must be positive")

        if self.search_results_per_page <= 0:
            raise ValueError("SEARCH_RESULTS_PER_PAGE must be positive")

        if self.rate_limit_requests_per_minute <= 0:
            raise ValueError("RATE_LIMIT_REQUESTS_PER_MINUTE must be positive")

        if self.rate_limit_burst <= 0:
            raise ValueError("RATE_LIMIT_BURST must be positive")

    def get_database_url(self, async_driver: bool = False) -> str:
        """Get database connection URL."""
        return self.database.get_connection_url(async_driver=async_driver)

    def get_database_engine_kwargs(self) -> dict:
        """Get database engine configuration."""
        return self.database.get_engine_kwargs()

    def get_jwt_config(self) -> dict:
        """Get JWT configuration."""
        return {
            "secret_key": self.jwt.secret_key,
            "algorithm": self.jwt.algorithm,
            "access_token_expire_minutes": self.jwt.access_token_expire_minutes,
        }

    def get_vendor_config(self) -> dict:
        """Get vendor configuration."""
        return {
            "max_products_per_vendor": self.vendor.max_products_per_vendor,
            "max_vendor_name_length": self.vendor.max_vendor_name_length,
            "max_vendor_description_length": self.vendor.max_vendor_description_length,
            "require_vendor_verification": self.vendor.require_vendor_verification,
            "verification_document_types": self.vendor.get_verification_document_types_list(),
            "allowed_statuses": self.vendor.get_allowed_statuses_list(),
        }

    def get_product_config(self) -> dict:
        """Get product configuration."""
        return {
            "max_product_name_length": self.product.max_product_name_length,
            "max_product_description_length": self.product.max_product_description_length,
            "max_images_per_product": self.product.max_images_per_product,
            "max_variants_per_product": self.product.max_variants_per_product,
            "allowed_categories": self.product.get_allowed_categories_list(),
            "enable_inventory_tracking": self.product.enable_inventory_tracking,
            "low_stock_threshold": self.product.low_stock_threshold,
        }

    def get_order_config(self) -> dict:
        """Get order configuration."""
        return {
            "max_items_per_order": self.order.max_items_per_order,
            "max_order_value": self.order.max_order_value,
            "allowed_statuses": self.order.get_allowed_statuses_list(),
            "payment_timeout_minutes": self.order.payment_timeout_minutes,
            "enable_partial_payments": self.order.enable_partial_payments,
        }

    def get_feature_config(self) -> dict:
        """Get feature configuration."""
        return {
            "enable_reviews": self.enable_reviews,
            "enable_staging": self.enable_staging,
            "enable_elasticsearch": self.enable_elasticsearch,
        }

    def get_file_config(self) -> dict:
        """Get file configuration."""
        return {
            "max_file_size_mb": self.max_file_size_mb,
            "allowed_file_types": self.allowed_file_types,
        }

    def get_rate_limit_config(self) -> dict:
        """Get rate limiting configuration."""
        return {
            "requests_per_minute": self.rate_limit_requests_per_minute,
            "burst": self.rate_limit_burst,
        }


# Global settings instance
_settings = None


def get_settings() -> VendorServiceSettings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = VendorServiceSettings()
    return _settings
