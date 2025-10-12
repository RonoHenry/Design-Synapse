"""Core LLM functionality for text processing."""

from functools import lru_cache
from typing import List, Optional
from sqlalchemy.orm import Session
from ..services.llm import LLMService
from ..models import Resource

# Mock resource and db for standalone functions
class _MockResource:
    """Mock resource for standalone functions."""
    def __init__(self):
        self.summary = ""
        self.key_takeaways = []
        self.keywords = []

class _MockDb:
    """Mock db for standalone functions."""
    def commit(self):
        pass

@lru_cache()
def get_llm_service() -> LLMService:
    """Get or create LLM service instance."""
    return LLMService()

async def summarize_text(text: str) -> str:
    """Summarize the given text."""
    service = get_llm_service()
    resource = _MockResource()
    db = _MockDb()
    result = await service.generate_insights(text, resource, db)
    return result[0]

async def extract_key_points(text: str, max_points: int = 5) -> List[str]:
    """Extract key points from the given text."""
    service = get_llm_service()
    resource = _MockResource()
    db = _MockDb()
    result = await service.generate_insights(text, resource, db)
    return result[1][:max_points]