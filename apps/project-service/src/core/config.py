"""
Project Service Configuration.

This module provides configuration management for the Project Service using
the unified configuration system with proper environment variable validation.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Add the packages directory to the Python path for shared config access
packages_path = Path(__file__).parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.config import BaseServiceConfig, DatabaseConfig, Environment


class ProjectSettings(BaseSettings):
    """Project-specific configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="PROJECT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Project limits
    max_projects_per_user: int = Field(default=100, ge=1, le=1000)
    max_project_name_length: int = Field(default=255, ge=10, le=500)
    max_project_description_length: int = Field(default=5000, ge=100, le=50000)
    
    # Project statuses
    allowed_statuses: str = Field(default="draft,in_progress,review,completed,archived")
    
    # Project sharing settings
    enable_project_sharing: bool = Field(default=True)
    max_collaborators_per_project: int = Field(default=10, ge=1, le=100)
    
    # Project templates
    enable_project_templates: bool = Field(default=True)
    max_custom_templates_per_user: int = Field(default=5, ge=0, le=50)
    
    @field_validator("allowed_statuses")
    @classmethod
    def validate_allowed_statuses(cls, v: str) -> str:
        """Validate project statuses."""
        if not v or not v.strip():
            raise ValueError("allowed_statuses cannot be empty")
        
        statuses = [s.strip().lower() for s in v.split(",")]
        
        # Ensure required statuses are present
        required_statuses = {"draft", "in_progress", "completed"}
        for status in required_statuses:
            if status not in statuses:
                raise ValueError(f"Required status '{status}' is missing from allowed_statuses")
        
        # Validate status names
        valid_chars = set("abcdefghijklmnopqrstuvwxyz_-")
        for status in statuses:
            if not status or len(status) > 50:
                raise ValueError(f"Invalid status name: '{status}' (must be 1-50 characters)")
            if not all(c in valid_chars for c in status):
                raise ValueError(f"Invalid status name: '{status}' (only lowercase letters, hyphens, and underscores allowed)")
        
        return v
    
    def get_allowed_statuses_list(self) -> List[str]:
        """Get list of allowed project statuses."""
        return [s.strip().lower() for s in self.allowed_statuses.split(",")]


class CommentSettings(BaseSettings):
    """Comment system configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="COMMENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Comment limits
    max_comment_length: int = Field(default=2000, ge=10, le=10000)
    max_comments_per_project: int = Field(default=1000, ge=10, le=10000)
    
    # Comment features
    enable_comment_editing: bool = Field(default=True)
    comment_edit_time_limit_minutes: int = Field(default=60, ge=1, le=1440)  # Max 24 hours
    enable_comment_threading: bool = Field(default=True)
    max_thread_depth: int = Field(default=5, ge=1, le=10)
    
    # Moderation
    enable_comment_moderation: bool = Field(default=False)
    auto_moderate_keywords: str = Field(default="")
    
    @field_validator("auto_moderate_keywords")
    @classmethod
    def validate_moderation_keywords(cls, v: str) -> str:
        """Validate moderation keywords."""
        if v and len(v.split(",")) > 100:
            raise ValueError("Maximum 100 moderation keywords allowed")
        return v
    
    def get_moderation_keywords_list(self) -> List[str]:
        """Get list of moderation keywords."""
        if not self.auto_moderate_keywords:
            return []
        return [k.strip().lower() for k in self.auto_moderate_keywords.split(",") if k.strip()]


class JWTSettings(BaseSettings):
    """JWT configuration for project service."""
    
    model_config = SettingsConfigDict(
        env_prefix="JWT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
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
            raise ValueError(f"algorithm must be one of: {', '.join(allowed_algorithms)}")
        return v


class ProjectServiceSettings:
    """Project Service configuration settings."""
    
    def __init__(self):
        # Initialize shared configurations
        self.base = BaseServiceConfig(
            service_name="project-service",
            service_version="1.0.0",
            port=8003
        )
        self.database = DatabaseConfig()
        self.jwt = JWTSettings()
        self.project = ProjectSettings()
        self.comment = CommentSettings()
        
        # Service-specific settings
        self.enable_project_analytics: bool = os.getenv("ENABLE_PROJECT_ANALYTICS", "true").lower() == "true"
        self.enable_project_export: bool = os.getenv("ENABLE_PROJECT_EXPORT", "true").lower() == "true"
        self.enable_project_import: bool = os.getenv("ENABLE_PROJECT_IMPORT", "true").lower() == "true"
        
        # Export/Import settings
        self.max_export_size_mb: int = int(os.getenv("MAX_EXPORT_SIZE_MB", "100"))
        self.supported_export_formats: List[str] = os.getenv("SUPPORTED_EXPORT_FORMATS", "json,csv,pdf").split(",")
        self.supported_import_formats: List[str] = os.getenv("SUPPORTED_IMPORT_FORMATS", "json,csv").split(",")
        
        # Performance settings
        self.max_concurrent_operations: int = int(os.getenv("MAX_CONCURRENT_OPERATIONS", "5"))
        self.operation_timeout_minutes: int = int(os.getenv("OPERATION_TIMEOUT_MINUTES", "15"))
        
        # API rate limiting
        self.rate_limit_requests_per_minute: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))
        self.rate_limit_burst: int = int(os.getenv("RATE_LIMIT_BURST", "30"))
        
        # Notification settings
        self.enable_email_notifications: bool = os.getenv("ENABLE_EMAIL_NOTIFICATIONS", "false").lower() == "true"
        self.notification_batch_size: int = int(os.getenv("NOTIFICATION_BATCH_SIZE", "50"))
        
        # Validate configuration
        self._validate_project_service_config()
    
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
    
    def _validate_project_service_config(self) -> None:
        """Validate project service specific configuration."""
        # Validate base configuration
        self.base.validate_required_settings()
        
        # Validate database configuration
        self.database.validate_connection_settings()
        
        # Validate project service specific settings
        if self.max_export_size_mb <= 0:
            raise ValueError("MAX_EXPORT_SIZE_MB must be positive")
        
        if self.max_concurrent_operations <= 0:
            raise ValueError("MAX_CONCURRENT_OPERATIONS must be positive")
        
        if self.operation_timeout_minutes <= 0:
            raise ValueError("OPERATION_TIMEOUT_MINUTES must be positive")
        
        if self.rate_limit_requests_per_minute <= 0:
            raise ValueError("RATE_LIMIT_REQUESTS_PER_MINUTE must be positive")
        
        if self.rate_limit_burst <= 0:
            raise ValueError("RATE_LIMIT_BURST must be positive")
        
        if self.notification_batch_size <= 0:
            raise ValueError("NOTIFICATION_BATCH_SIZE must be positive")
        
        # Validate export/import formats
        valid_export_formats = {"json", "csv", "pdf", "xlsx"}
        for fmt in self.supported_export_formats:
            if fmt.strip().lower() not in valid_export_formats:
                raise ValueError(f"Unsupported export format: {fmt}")
        
        valid_import_formats = {"json", "csv", "xlsx"}
        for fmt in self.supported_import_formats:
            if fmt.strip().lower() not in valid_import_formats:
                raise ValueError(f"Unsupported import format: {fmt}")
    
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
    
    def get_project_config(self) -> dict:
        """Get project configuration."""
        return {
            "max_projects_per_user": self.project.max_projects_per_user,
            "max_project_name_length": self.project.max_project_name_length,
            "max_project_description_length": self.project.max_project_description_length,
            "allowed_statuses": self.project.get_allowed_statuses_list(),
            "enable_project_sharing": self.project.enable_project_sharing,
            "max_collaborators_per_project": self.project.max_collaborators_per_project,
            "enable_project_templates": self.project.enable_project_templates,
            "max_custom_templates_per_user": self.project.max_custom_templates_per_user,
        }
    
    def get_comment_config(self) -> dict:
        """Get comment configuration."""
        return {
            "max_comment_length": self.comment.max_comment_length,
            "max_comments_per_project": self.comment.max_comments_per_project,
            "enable_comment_editing": self.comment.enable_comment_editing,
            "comment_edit_time_limit_minutes": self.comment.comment_edit_time_limit_minutes,
            "enable_comment_threading": self.comment.enable_comment_threading,
            "max_thread_depth": self.comment.max_thread_depth,
            "enable_comment_moderation": self.comment.enable_comment_moderation,
            "moderation_keywords": self.comment.get_moderation_keywords_list(),
        }
    
    def get_feature_config(self) -> dict:
        """Get feature configuration."""
        return {
            "enable_project_analytics": self.enable_project_analytics,
            "enable_project_export": self.enable_project_export,
            "enable_project_import": self.enable_project_import,
            "max_export_size_mb": self.max_export_size_mb,
            "supported_export_formats": self.supported_export_formats,
            "supported_import_formats": self.supported_import_formats,
            "enable_email_notifications": self.enable_email_notifications,
        }
    
    def get_performance_config(self) -> dict:
        """Get performance configuration."""
        return {
            "max_concurrent_operations": self.max_concurrent_operations,
            "operation_timeout_minutes": self.operation_timeout_minutes,
            "notification_batch_size": self.notification_batch_size,
        }
    
    def get_rate_limit_config(self) -> dict:
        """Get rate limiting configuration."""
        return {
            "requests_per_minute": self.rate_limit_requests_per_minute,
            "burst": self.rate_limit_burst,
        }


# Global settings instance
settings = ProjectServiceSettings()


# Legacy compatibility - maintain the old interface for existing code
class Settings:
    """Legacy settings class for backward compatibility."""
    
    def __init__(self):
        self._settings = settings
    
    @property
    def JWT_SECRET_KEY(self) -> str:
        return self._settings.jwt.secret_key
    
    @property
    def JWT_ALGORITHM(self) -> str:
        return self._settings.jwt.algorithm
    
    @property
    def JWT_ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return self._settings.jwt.access_token_expire_minutes
    
    @property
    def MAX_PROJECTS_PER_USER(self) -> int:
        return self._settings.project.max_projects_per_user
    
    @property
    def MAX_PROJECT_NAME_LENGTH(self) -> int:
        return self._settings.project.max_project_name_length
    
    @property
    def MAX_PROJECT_DESCRIPTION_LENGTH(self) -> int:
        return self._settings.project.max_project_description_length
    
    @property
    def ALLOWED_PROJECT_STATUSES(self) -> List[str]:
        return self._settings.project.get_allowed_statuses_list()


# Legacy settings instance for backward compatibility
legacy_settings = Settings()