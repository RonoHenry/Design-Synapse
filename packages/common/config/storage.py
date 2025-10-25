"""
Storage configuration classes for DesignSynapse services.

This module provides configuration classes for managing file storage
with S3 integration, CDN support, and lifecycle policies.
"""

import os
from typing import Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from botocore.config import Config


# AWS regions supported for S3
SUPPORTED_AWS_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1", "eu-north-1",
    "ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "ap-northeast-2", 
    "ap-south-1", "ap-east-1", "ca-central-1", "sa-east-1", "af-south-1",
    "me-south-1"
]

# Default file extensions allowed for upload
DEFAULT_ALLOWED_EXTENSIONS = "jpg,jpeg,png,gif,pdf,dwg,step,ifc"

# File size limits (in MB)
MIN_FILE_SIZE_MB = 1
MAX_FILE_SIZE_MB = 1000

# Lifecycle policy defaults
DEFAULT_TRANSITION_DAYS = 30
DEFAULT_EXPIRATION_DAYS = 365
DEFAULT_MULTIPART_ABORT_DAYS = 7


class StorageConfig(BaseSettings):
    """
    Storage configuration with S3 integration and CDN support.
    
    This class manages configuration for file storage operations including:
    - S3 bucket and authentication settings
    - CDN integration for performance optimization
    - File upload restrictions and validation
    - Lifecycle policies for cost optimization
    
    Environment variables are prefixed with 'STORAGE_' (e.g., STORAGE_S3_BUCKET).
    """

    model_config = SettingsConfigDict(
        env_prefix="STORAGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # S3 settings
    s3_bucket: str = Field(..., min_length=1)
    s3_region: str = Field(..., min_length=1)
    s3_access_key_id: str = Field(..., min_length=1)
    s3_secret_access_key: str = Field(..., min_length=1)

    # CDN settings
    cdn_url: Optional[str] = None
    cdn_enabled: bool = False

    # Upload settings
    max_file_size_mb: int = Field(
        default=100, 
        ge=MIN_FILE_SIZE_MB, 
        le=MAX_FILE_SIZE_MB,
        description="Maximum file size allowed for upload in MB"
    )
    allowed_extensions_str: str = Field(
        default=DEFAULT_ALLOWED_EXTENSIONS, 
        alias="allowed_extensions",
        description="Comma-separated list of allowed file extensions"
    )

    @property
    def allowed_extensions(self) -> List[str]:
        """Get allowed extensions as a list of lowercase strings."""
        return [ext.strip().lower() for ext in self.allowed_extensions_str.split(",")]

    # Lifecycle settings
    lifecycle_enabled: bool = Field(
        default=False,
        description="Enable S3 lifecycle policies for cost optimization"
    )
    lifecycle_transition_days: int = Field(
        default=DEFAULT_TRANSITION_DAYS, 
        ge=1,
        description="Days after which files transition to Infrequent Access storage"
    )
    lifecycle_expiration_days: int = Field(
        default=DEFAULT_EXPIRATION_DAYS, 
        ge=1,
        description="Days after which files are automatically deleted"
    )

    @field_validator("s3_region")
    @classmethod
    def validate_s3_region(cls, v: str) -> str:
        """Validate AWS region format."""
        if v not in SUPPORTED_AWS_REGIONS:
            raise ValueError(
                f"s3_region must be a valid AWS region. Got: {v}. "
                f"Supported regions: {', '.join(SUPPORTED_AWS_REGIONS)}"
            )
        return v

    @field_validator("max_file_size_mb")
    @classmethod
    def validate_max_file_size(cls, v: int) -> int:
        """Validate max file size is reasonable."""
        if v <= 0:
            raise ValueError("max_file_size_mb must be greater than 0")
        return v

    @field_validator("lifecycle_transition_days", "lifecycle_expiration_days")
    @classmethod
    def validate_lifecycle_days(cls, v: int, info) -> int:
        """Validate lifecycle days are positive."""
        if v < 0:
            raise ValueError(f"{info.field_name} must be non-negative")
        return v

    def get_s3_client_kwargs(self) -> Dict:
        """Generate S3 client configuration."""
        return {
            "aws_access_key_id": self.s3_access_key_id,
            "aws_secret_access_key": self.s3_secret_access_key,
            "region_name": self.s3_region,
            "config": Config(
                retries={"max_attempts": 3, "mode": "adaptive"},
                max_pool_connections=50,
            ),
        }

    def get_upload_settings(self) -> Dict:
        """Get upload configuration settings."""
        return {
            "max_file_size_bytes": self.max_file_size_mb * 1024 * 1024,
            "allowed_extensions": self.allowed_extensions,
            "enable_compression": True,
            "compression_quality": 85,
        }

    def get_lifecycle_settings(self) -> Dict:
        """Get lifecycle policy settings for S3 bucket management."""
        return {
            "enabled": self.lifecycle_enabled,
            "transition_to_ia_days": self.lifecycle_transition_days,
            "expiration_days": self.lifecycle_expiration_days,
            "abort_incomplete_multipart_days": DEFAULT_MULTIPART_ABORT_DAYS,
        }

    def get_file_url(self, file_key: str) -> str:
        """Generate file URL (CDN or S3 direct)."""
        if self.cdn_enabled and self.cdn_url:
            return f"{self.cdn_url.rstrip('/')}/{file_key}"
        else:
            return f"https://{self.s3_bucket}.s3.{self.s3_region}.amazonaws.com/{file_key}"

    def is_allowed_extension(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        if "." not in filename:
            return False
        
        extension = filename.rsplit(".", 1)[1].lower()
        return extension in self.allowed_extensions

    def is_valid_file_size(self, file_size_bytes: int) -> bool:
        """Check if file size is within limits."""
        if file_size_bytes <= 0:
            return False
        
        max_bytes = self.max_file_size_mb * 1024 * 1024
        return file_size_bytes <= max_bytes

    def get_s3_lifecycle_policy(self) -> Optional[Dict]:
        """
        Generate S3 lifecycle policy configuration.
        
        Returns:
            Dict containing lifecycle policy rules if enabled, None otherwise.
        """
        if not self.lifecycle_enabled:
            return None
            
        return {
            "Rules": [
                {
                    "ID": "DesignSynapseLifecycleRule",
                    "Status": "Enabled",
                    "Filter": {"Prefix": ""},
                    "Transitions": [
                        {
                            "Days": self.lifecycle_transition_days,
                            "StorageClass": "STANDARD_IA"
                        }
                    ],
                    "Expiration": {
                        "Days": self.lifecycle_expiration_days
                    },
                    "AbortIncompleteMultipartUpload": {
                        "DaysAfterInitiation": DEFAULT_MULTIPART_ABORT_DAYS
                    }
                }
            ]
        }

    def validate_required_settings(self) -> None:
        """Validate that required settings are present and valid."""
        if not self.s3_access_key_id or not self.s3_secret_access_key:
            raise ValueError("S3 credentials (access key and secret key) are required")
        
        if not self.s3_bucket:
            raise ValueError("S3 bucket name is required")
        
        if not self.s3_region:
            raise ValueError("S3 region is required")
            
        # Validate lifecycle settings consistency
        if self.lifecycle_enabled and self.lifecycle_transition_days >= self.lifecycle_expiration_days:
            raise ValueError(
                "lifecycle_transition_days must be less than lifecycle_expiration_days"
            )