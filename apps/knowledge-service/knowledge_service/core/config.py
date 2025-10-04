"""
Knowledge Service Configuration.

This module provides configuration management for the Knowledge Service using
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

from common.config import (
    BaseServiceConfig, 
    DatabaseConfig, 
    LLMConfig, 
    VectorConfig,
    Environment,
    LLMProvider,
    VectorProvider
)


class FileProcessingSettings(BaseSettings):
    """File processing configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="FILE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # File size limits
    max_file_size_mb: int = Field(default=50, ge=1, le=500)  # Max 500MB
    max_batch_size: int = Field(default=10, ge=1, le=100)
    
    # Supported file types
    supported_types: str = Field(default="pdf,docx,txt,md,html")
    
    # Processing settings
    chunk_size: int = Field(default=1000, ge=100, le=5000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)
    
    # Storage settings
    storage_path: str = Field(default="./storage/files")
    temp_path: str = Field(default="./storage/temp")
    
    @field_validator("supported_types")
    @classmethod
    def validate_supported_types(cls, v: str) -> str:
        """Validate supported file types."""
        if not v or not v.strip():
            raise ValueError("supported_types cannot be empty")
        
        valid_types = {"pdf", "docx", "txt", "md", "html", "rtf", "odt"}
        types = [t.strip().lower() for t in v.split(",")]
        
        for file_type in types:
            if file_type not in valid_types:
                raise ValueError(f"Unsupported file type: {file_type}. Valid types: {', '.join(valid_types)}")
        
        return v
    
    @field_validator("chunk_overlap")
    @classmethod
    def validate_chunk_overlap(cls, v: int, info) -> int:
        """Validate chunk overlap is reasonable."""
        # We can't access chunk_size here directly, so we'll validate in the main config
        return v
    
    def get_supported_types_list(self) -> List[str]:
        """Get list of supported file types."""
        return [t.strip().lower() for t in self.supported_types.split(",")]
    
    def validate_file_processing_config(self) -> None:
        """Validate file processing configuration."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        
        # Ensure storage directories exist or can be created
        for path in [self.storage_path, self.temp_path]:
            try:
                Path(path).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValueError(f"Cannot create storage directory {path}: {e}")


class SearchSettings(BaseSettings):
    """Search and retrieval configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="SEARCH_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Search parameters
    default_top_k: int = Field(default=10, ge=1, le=100)
    max_top_k: int = Field(default=50, ge=1, le=200)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    
    # Reranking settings
    enable_reranking: bool = Field(default=True)
    rerank_top_k: int = Field(default=20, ge=1, le=100)
    
    # Caching settings
    enable_search_cache: bool = Field(default=True)
    cache_ttl_minutes: int = Field(default=60, ge=1, le=1440)  # Max 24 hours
    
    @field_validator("max_top_k")
    @classmethod
    def validate_max_top_k(cls, v: int, info) -> int:
        """Validate max_top_k is reasonable."""
        if hasattr(info.data, 'default_top_k') and v < info.data['default_top_k']:
            raise ValueError("max_top_k must be greater than or equal to default_top_k")
        return v


class KnowledgeServiceSettings:
    """Knowledge Service configuration settings."""
    
    def __init__(self):
        # Initialize shared configurations
        self.base = BaseServiceConfig(
            service_name="knowledge-service",
            service_version="1.0.0",
            port=8002
        )
        self.database = DatabaseConfig()
        self.llm = LLMConfig()
        self.vector = VectorConfig()
        self.file_processing = FileProcessingSettings()
        self.search = SearchSettings()
        
        # Knowledge service specific settings
        self.enable_auto_tagging: bool = os.getenv("ENABLE_AUTO_TAGGING", "true").lower() == "true"
        self.enable_summary_generation: bool = os.getenv("ENABLE_SUMMARY_GENERATION", "true").lower() == "true"
        self.enable_key_takeaways: bool = os.getenv("ENABLE_KEY_TAKEAWAYS", "true").lower() == "true"
        
        # Processing queue settings
        self.max_concurrent_processing: int = int(os.getenv("MAX_CONCURRENT_PROCESSING", "3"))
        self.processing_timeout_minutes: int = int(os.getenv("PROCESSING_TIMEOUT_MINUTES", "30"))
        
        # API rate limiting
        self.rate_limit_requests_per_minute: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "100"))
        self.rate_limit_burst: int = int(os.getenv("RATE_LIMIT_BURST", "20"))
        
        # Content analysis settings
        self.min_content_length: int = int(os.getenv("MIN_CONTENT_LENGTH", "100"))
        self.max_content_length: int = int(os.getenv("MAX_CONTENT_LENGTH", "1000000"))  # 1MB of text
        
        # Validate configuration
        self._validate_knowledge_service_config()
    
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
    
    def _validate_knowledge_service_config(self) -> None:
        """Validate knowledge service specific configuration."""
        # Validate base configuration
        self.base.validate_required_settings()
        
        # Validate database configuration
        self.database.validate_connection_settings()
        
        # Validate LLM configuration
        self.llm.validate_configuration()
        
        # Validate vector configuration
        self.vector.validate_configuration()
        
        # Validate file processing configuration
        self.file_processing.validate_file_processing_config()
        
        # Validate knowledge service specific settings
        if self.max_concurrent_processing <= 0:
            raise ValueError("MAX_CONCURRENT_PROCESSING must be positive")
        
        if self.processing_timeout_minutes <= 0:
            raise ValueError("PROCESSING_TIMEOUT_MINUTES must be positive")
        
        if self.rate_limit_requests_per_minute <= 0:
            raise ValueError("RATE_LIMIT_REQUESTS_PER_MINUTE must be positive")
        
        if self.rate_limit_burst <= 0:
            raise ValueError("RATE_LIMIT_BURST must be positive")
        
        if self.min_content_length <= 0:
            raise ValueError("MIN_CONTENT_LENGTH must be positive")
        
        if self.max_content_length <= self.min_content_length:
            raise ValueError("MAX_CONTENT_LENGTH must be greater than MIN_CONTENT_LENGTH")
        
        # Validate that required features have necessary providers
        if (self.enable_summary_generation or self.enable_key_takeaways or self.enable_auto_tagging):
            if not self.llm.primary_provider:
                raise ValueError("LLM provider is required for content analysis features")
    
    def get_database_url(self, async_driver: bool = False) -> str:
        """Get database connection URL."""
        return self.database.get_connection_url(async_driver=async_driver)
    
    def get_database_engine_kwargs(self) -> dict:
        """Get database engine configuration."""
        return self.database.get_engine_kwargs()
    
    def get_llm_config(self) -> dict:
        """Get LLM configuration."""
        return {
            "primary_provider": self.llm.primary_provider,
            "fallback_providers": self.llm.fallback_providers,
            "max_retries": self.llm.max_retries,
            "timeout": self.llm.timeout,
            "provider_configs": {
                provider: self.llm.get_provider_config(provider)
                for provider in self.llm.get_all_providers()
            }
        }
    
    def get_vector_config(self) -> dict:
        """Get vector database configuration."""
        return {
            "provider": self.vector.provider,
            "provider_config": self.vector.get_provider_config(),
            "search_config": self.vector.get_search_config(),
        }
    
    def get_file_processing_config(self) -> dict:
        """Get file processing configuration."""
        return {
            "max_file_size_mb": self.file_processing.max_file_size_mb,
            "max_batch_size": self.file_processing.max_batch_size,
            "supported_types": self.file_processing.get_supported_types_list(),
            "chunk_size": self.file_processing.chunk_size,
            "chunk_overlap": self.file_processing.chunk_overlap,
            "storage_path": self.file_processing.storage_path,
            "temp_path": self.file_processing.temp_path,
        }
    
    def get_search_config(self) -> dict:
        """Get search configuration."""
        return {
            "default_top_k": self.search.default_top_k,
            "max_top_k": self.search.max_top_k,
            "similarity_threshold": self.search.similarity_threshold,
            "enable_reranking": self.search.enable_reranking,
            "rerank_top_k": self.search.rerank_top_k,
            "enable_search_cache": self.search.enable_search_cache,
            "cache_ttl_minutes": self.search.cache_ttl_minutes,
        }
    
    def get_processing_config(self) -> dict:
        """Get processing configuration."""
        return {
            "enable_auto_tagging": self.enable_auto_tagging,
            "enable_summary_generation": self.enable_summary_generation,
            "enable_key_takeaways": self.enable_key_takeaways,
            "max_concurrent_processing": self.max_concurrent_processing,
            "processing_timeout_minutes": self.processing_timeout_minutes,
            "min_content_length": self.min_content_length,
            "max_content_length": self.max_content_length,
        }
    
    def get_rate_limit_config(self) -> dict:
        """Get rate limiting configuration."""
        return {
            "requests_per_minute": self.rate_limit_requests_per_minute,
            "burst": self.rate_limit_burst,
        }


# Global settings instance
settings = KnowledgeServiceSettings()