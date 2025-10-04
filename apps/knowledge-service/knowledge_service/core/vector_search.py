"""Dependencies and configuration for vector search service."""

from functools import lru_cache
from ..services.vector_search import VectorSearchService

@lru_cache()
def get_vector_search_service() -> VectorSearchService:
    """Get or create vector search service instance."""
    return VectorSearchService()