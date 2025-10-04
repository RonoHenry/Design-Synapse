"""Basic LLM service test."""

import os
import pytest
import httpx
from knowledge_service.services.llm import LLMService


class MockResponse:
    """Mock HTTPX Response"""
    def __init__(self, status_code=200, content="Test summary.\n\n- Point 1\n- Point 2\n\nkey1, key2"):
        self.status_code = status_code
        self._content = content
        self.request = httpx.Request('POST', 'https://api.openai.com/v1/chat/completions')

    def json(self):
        return {
            "choices": [{
                "message": {
                    "content": self._content
                }
            }]
        }

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(f"HTTP {self.status_code}", request=self.request, response=self)


class MockClient:
    """Mock HTTP client."""
    def __init__(self):
        self.headers = {
            "Authorization": "Bearer dummy-key",
            "Content-Type": "application/json"
        }

    async def post(self, *args, **kwargs):
        return MockResponse()

    async def aclose(self):
        pass


@pytest.fixture
def llm_service(monkeypatch):
    """Create LLMService instance for testing."""
    monkeypatch.setenv('OPENAI_API_KEY', 'dummy-key')
    service = LLMService()
    service._client = MockClient()
    return service


@pytest.mark.asyncio
async def test_basic_llm(llm_service):
    """Test basic LLM functionality."""
    class MockResource:
        def __init__(self):
            self.summary = None
            self.key_takeaways = None
            self.keywords = None

    class MockDb:
        def commit(self):
            pass

    resource = MockResource()
    db = MockDb()

    summary, key_points, keywords = await llm_service.generate_insights("Test content", resource, db)
    assert isinstance(summary, str)
    assert len(summary) > 0
    assert isinstance(key_points, list)
    assert len(key_points) > 0
    assert isinstance(keywords, list)
    assert len(keywords) > 0