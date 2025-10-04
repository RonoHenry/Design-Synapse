import os
import pytest
import httpx
from knowledge_service.services.llm import LLMService

class MockResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code
        self.request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")

    def json(self):
        return {
            "choices": [{
                "message": {
                    "content": """This is a mock summary.

- Point 1
- Point 2
- Point 3

keyword1, keyword2, keyword3"""
                }
            }]
        }

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(f"HTTP {self.status_code}", request=self.request, response=self)

class MockClient:
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
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")
    service = LLMService()
    service._client = MockClient()
    return service

@pytest.mark.asyncio
async def test_basic_llm(llm_service):
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
