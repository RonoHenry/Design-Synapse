"""Configuration management for knowledge service."""

import os
from pathlib import Path
from typing import List, Optional


class KnowledgeServiceConfig:
    """Simple configuration for knowledge service."""

    def __init__(self):
        # File processing settings
        self._max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
        self._allowed_file_types = [".pdf", ".docx", ".txt", ".md", ".html"]
        self._storage_path = os.getenv("STORAGE_PATH", "storage/knowledge")

        # LLM settings
        self._openai_api_key = os.getenv("OPENAI_API_KEY")
        self._openai_model = os.getenv("OPENAI_MODEL", "gpt-4")
        self._openai_temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        self._openai_max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))

        # Vector search settings
        self._pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self._pinecone_environment = os.getenv("PINECONE_ENVIRONMENT")
        self._pinecone_index_name = os.getenv(
            "PINECONE_INDEX_NAME", "knowledge-resources"
        )
        self._embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self._embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "384"))

        # Performance settings
        self._max_content_length = int(os.getenv("MAX_CONTENT_LENGTH", "1000000"))
        self._max_query_length = int(os.getenv("MAX_QUERY_LENGTH", "10000"))
        self._search_timeout_seconds = int(os.getenv("SEARCH_TIMEOUT_SECONDS", "30"))

        # Batch processing settings
        self._batch_size = int(os.getenv("BATCH_SIZE", "10"))
        self._concurrent_limit = int(os.getenv("CONCURRENT_LIMIT", "5"))

    # File processing settings
    @property
    def max_file_size_mb(self) -> int:
        return self._max_file_size_mb

    @property
    def allowed_file_types(self) -> List[str]:
        return self._allowed_file_types

    @property
    def storage_path(self) -> str:
        return self._storage_path

    # LLM settings
    @property
    def openai_api_key(self) -> Optional[str]:
        return self._openai_api_key

    @property
    def openai_model(self) -> str:
        return self._openai_model

    @property
    def openai_temperature(self) -> float:
        return self._openai_temperature

    @property
    def openai_max_tokens(self) -> int:
        return self._openai_max_tokens

    # Vector search settings
    @property
    def pinecone_api_key(self) -> Optional[str]:
        return self._pinecone_api_key

    @property
    def pinecone_environment(self) -> Optional[str]:
        return self._pinecone_environment

    @property
    def pinecone_index_name(self) -> str:
        return self._pinecone_index_name

    @property
    def embedding_model(self) -> str:
        return self._embedding_model

    @property
    def embedding_dimension(self) -> int:
        return self._embedding_dimension

    # Performance settings
    @property
    def max_content_length(self) -> int:
        return self._max_content_length

    @property
    def max_query_length(self) -> int:
        return self._max_query_length

    @property
    def search_timeout_seconds(self) -> int:
        return self._search_timeout_seconds

    # Batch processing settings
    @property
    def batch_size(self) -> int:
        return self._batch_size

    @property
    def concurrent_limit(self) -> int:
        return self._concurrent_limit


def get_config() -> KnowledgeServiceConfig:
    """Get configuration instance."""
    return KnowledgeServiceConfig()
