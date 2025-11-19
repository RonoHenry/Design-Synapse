"""Dependencies and configuration for vector search service."""

from functools import lru_cache
from ..interfaces.services import IVectorSearchService

@lru_cache()
def get_vector_search_service() -> IVectorSearchService:
    """Get or create vector search service instance."""
    # Import here to avoid circular imports
    from ..services.vector_search import VectorSearchService
    return VectorSearchService()