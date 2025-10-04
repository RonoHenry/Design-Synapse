"""
Vector database configuration classes.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class VectorProvider(str, Enum):
    """Supported vector database providers."""
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    QDRANT = "qdrant"
    CHROMA = "chroma"


class VectorMetric(str, Enum):
    """Supported vector similarity metrics."""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOTPRODUCT = "dotproduct"


class VectorConfig(BaseSettings):
    """Vector database configuration with proper validation."""
    
    model_config = SettingsConfigDict(
        env_prefix="VECTOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Provider settings
    provider: VectorProvider = VectorProvider.PINECONE
    
    # Pinecone settings
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    pinecone_index_name: str = "knowledge-base"
    
    # Weaviate settings
    weaviate_url: Optional[str] = None
    weaviate_api_key: Optional[str] = None
    weaviate_class_name: str = "Resource"
    
    # Qdrant settings
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None
    qdrant_collection_name: str = "resources"
    
    # Chroma settings
    chroma_host: str = "localhost"
    chroma_port: int = Field(default=8000, ge=1, le=65535)
    chroma_collection_name: str = "resources"
    
    # Vector settings
    dimension: int = Field(default=384, ge=1, le=4096)
    metric: VectorMetric = VectorMetric.COSINE
    
    # Search settings
    top_k: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    
    # Performance settings
    batch_size: int = Field(default=100, ge=1, le=1000)
    timeout: int = Field(default=30, ge=1, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    @field_validator("pinecone_index_name", "weaviate_class_name", "qdrant_collection_name", "chroma_collection_name")
    @classmethod
    def validate_names(cls, v: str) -> str:
        """Validate collection/index names."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Collection/index name cannot be empty")
        if len(v) > 100:
            raise ValueError("Collection/index name cannot exceed 100 characters")
        return v.strip()
    
    @model_validator(mode="after")
    def validate_provider_credentials(self) -> "VectorConfig":
        """Validate that required credentials are provided for the selected provider."""
        if self.provider == VectorProvider.PINECONE:
            if not self.pinecone_api_key:
                raise ValueError(
                    "VECTOR_PINECONE_API_KEY environment variable is required when using Pinecone"
                )
            if not self.pinecone_environment:
                raise ValueError(
                    "VECTOR_PINECONE_ENVIRONMENT environment variable is required when using Pinecone"
                )
        elif self.provider == VectorProvider.WEAVIATE:
            if not self.weaviate_url:
                raise ValueError(
                    "VECTOR_WEAVIATE_URL environment variable is required when using Weaviate"
                )
        elif self.provider == VectorProvider.QDRANT:
            if not self.qdrant_url:
                raise ValueError(
                    "VECTOR_QDRANT_URL environment variable is required when using Qdrant"
                )
        
        return self
    
    def get_provider_config(self) -> Dict[str, Any]:
        """Get configuration for the selected provider."""
        if self.provider == VectorProvider.PINECONE:
            return {
                "api_key": self.pinecone_api_key,
                "environment": self.pinecone_environment,
                "index_name": self.pinecone_index_name,
                "dimension": self.dimension,
                "metric": self.metric.value,
            }
        elif self.provider == VectorProvider.WEAVIATE:
            config = {
                "url": self.weaviate_url,
                "class_name": self.weaviate_class_name,
                "dimension": self.dimension,
            }
            if self.weaviate_api_key:
                config["api_key"] = self.weaviate_api_key
            return config
        elif self.provider == VectorProvider.QDRANT:
            config = {
                "url": self.qdrant_url,
                "collection_name": self.qdrant_collection_name,
                "dimension": self.dimension,
                "metric": self.metric.value,
            }
            if self.qdrant_api_key:
                config["api_key"] = self.qdrant_api_key
            return config
        elif self.provider == VectorProvider.CHROMA:
            return {
                "host": self.chroma_host,
                "port": self.chroma_port,
                "collection_name": self.chroma_collection_name,
                "dimension": self.dimension,
            }
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def get_search_config(self) -> Dict[str, Any]:
        """Get search configuration."""
        return {
            "top_k": self.top_k,
            "similarity_threshold": self.similarity_threshold,
            "timeout": self.timeout,
        }
    
    def validate_configuration(self) -> None:
        """Validate the complete vector configuration."""
        # Validate dimension is appropriate for the metric
        if self.metric == VectorMetric.DOTPRODUCT and self.dimension < 2:
            raise ValueError("Dot product metric requires at least 2 dimensions")
        
        # Validate search settings
        if self.top_k <= 0:
            raise ValueError("top_k must be positive")
        if not (0.0 <= self.similarity_threshold <= 1.0):
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        
        # Validate batch size is reasonable
        if self.batch_size > 1000:
            raise ValueError("batch_size should not exceed 1000 for performance reasons")