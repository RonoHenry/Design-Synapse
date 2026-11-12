"""Service factory for dependency injection."""

from functools import lru_cache
from typing import Optional

from ..config import KnowledgeServiceConfig, get_config
from ..interfaces.services import (ILLMService, IPDFProcessingService,
                                   IVectorSearchService)
from .llm import LLMService
from .pdf_processing import PDFProcessingService
from .recommendation import RecommendationService
from .vector_search import VectorSearchService


class ServiceFactory:
    """Factory for creating service instances."""

    def __init__(self, config=None):
        from ..config import get_config

        self.config = config or get_config()
        self._pdf_service = None
        self._llm_service = None
        self._vector_service = None
        self._recommendation_service = None

    def get_pdf_service(self) -> IPDFProcessingService:
        """Get PDF processing service instance."""
        if self._pdf_service is None:
            self._pdf_service = PDFProcessingService()
        return self._pdf_service

    def get_llm_service(self) -> ILLMService:
        """Get LLM service instance."""
        if self._llm_service is None:
            self._llm_service = LLMService(self.config)
        return self._llm_service

    def get_vector_service(self) -> IVectorSearchService:
        """Get vector search service instance."""
        if self._vector_service is None:
            self._vector_service = VectorSearchService(self.config)
        return self._vector_service

    async def get_recommendation_service(self) -> RecommendationService:
        """Get recommendation service instance."""
        if self._recommendation_service is None:
            vector_service = self.get_vector_service()
            llm_service = self.get_llm_service()
            self._recommendation_service = RecommendationService(
                vector_service, llm_service
            )
        return self._recommendation_service


# Global factory instance
_factory = None


@lru_cache()
def get_service_factory() -> ServiceFactory:
    """Get global service factory instance."""
    global _factory
    if _factory is None:
        _factory = ServiceFactory()
    return _factory


def get_pdf_service() -> IPDFProcessingService:
    """Get PDF processing service."""
    return get_service_factory().get_pdf_service()


def get_llm_service() -> ILLMService:
    """Get LLM service."""
    return get_service_factory().get_llm_service()


def get_vector_service() -> IVectorSearchService:
    """Get vector search service."""
    return get_service_factory().get_vector_service()


async def get_recommendation_service() -> RecommendationService:
    """Get recommendation service."""
    return await get_service_factory().get_recommendation_service()


async def get_recommendation_service() -> RecommendationService:
    """Get recommendation service."""
    return await get_service_factory().get_recommendation_service()
