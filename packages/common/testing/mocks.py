"""
Mock utilities for external services used in testing.
"""

from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, Mock
import asyncio
import json
from datetime import datetime


class MockExternalService:
    """Base class for mocking external services."""
    
    def __init__(self, fail_rate: float = 0.0, delay: float = 0.0):
        """
        Initialize mock service.
        
        Args:
            fail_rate: Probability of failure (0.0 to 1.0)
            delay: Artificial delay in seconds
        """
        self.fail_rate = fail_rate
        self.delay = delay
        self.call_count = 0
        self.call_history = []
    
    async def _simulate_delay(self):
        """Simulate network delay."""
        if self.delay > 0:
            await asyncio.sleep(self.delay)
    
    def _should_fail(self) -> bool:
        """Determine if this call should fail based on fail_rate."""
        import random
        return random.random() < self.fail_rate
    
    def _record_call(self, method: str, *args, **kwargs):
        """Record method call for testing verification."""
        self.call_count += 1
        self.call_history.append({
            "method": method,
            "args": args,
            "kwargs": kwargs,
            "timestamp": datetime.utcnow()
        })


class MockLLMService(MockExternalService):
    """Mock LLM service for testing."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.responses = {
            "summary": "This is a test summary of the content.",
            "key_takeaways": [
                "Key insight number one",
                "Important finding number two", 
                "Critical observation number three"
            ],
            "keywords": ["test", "mock", "example", "content"],
            "analysis": "Detailed analysis of the content would go here."
        }
    
    async def generate_summary(self, content: str, max_length: int = 500) -> str:
        """Mock summary generation."""
        await self._simulate_delay()
        self._record_call("generate_summary", content=content, max_length=max_length)
        
        if self._should_fail():
            raise Exception("LLM service temporarily unavailable")
        
        return self.responses["summary"][:max_length]
    
    async def extract_key_takeaways(self, content: str, max_count: int = 5) -> List[str]:
        """Mock key takeaway extraction."""
        await self._simulate_delay()
        self._record_call("extract_key_takeaways", content=content, max_count=max_count)
        
        if self._should_fail():
            raise Exception("LLM service temporarily unavailable")
        
        return self.responses["key_takeaways"][:max_count]
    
    async def extract_keywords(self, content: str, max_count: int = 10) -> List[str]:
        """Mock keyword extraction."""
        await self._simulate_delay()
        self._record_call("extract_keywords", content=content, max_count=max_count)
        
        if self._should_fail():
            raise Exception("LLM service temporarily unavailable")
        
        return self.responses["keywords"][:max_count]
    
    async def analyze_content(self, content: str) -> Dict[str, Any]:
        """Mock comprehensive content analysis."""
        await self._simulate_delay()
        self._record_call("analyze_content", content=content)
        
        if self._should_fail():
            raise Exception("LLM service temporarily unavailable")
        
        return {
            "summary": await self.generate_summary(content),
            "key_takeaways": await self.extract_key_takeaways(content),
            "keywords": await self.extract_keywords(content),
            "analysis": self.responses["analysis"]
        }
    
    def set_response(self, response_type: str, value: Any):
        """Set custom response for testing."""
        self.responses[response_type] = value


class MockVectorService(MockExternalService):
    """Mock vector search service for testing."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.index_data = {}
        self.search_results = [
            {
                "id": "1",
                "score": 0.95,
                "metadata": {
                    "title": "Test Document 1",
                    "content_type": "pdf",
                    "author": "Test Author"
                }
            },
            {
                "id": "2", 
                "score": 0.87,
                "metadata": {
                    "title": "Test Document 2",
                    "content_type": "web",
                    "author": "Another Author"
                }
            }
        ]
    
    async def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock vector upsert operation."""
        await self._simulate_delay()
        self._record_call("upsert_vectors", vectors=vectors, namespace=namespace)
        
        if self._should_fail():
            raise Exception("Vector service temporarily unavailable")
        
        # Store vectors in mock index
        for vector in vectors:
            vector_id = vector.get("id")
            if vector_id:
                self.index_data[vector_id] = vector
        
        return {
            "upserted_count": len(vectors),
            "namespace": namespace or "default"
        }
    
    async def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 10,
        namespace: Optional[str] = None,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Mock vector search operation."""
        await self._simulate_delay()
        self._record_call(
            "search_vectors",
            query_vector=query_vector,
            top_k=top_k,
            namespace=namespace,
            filter_dict=filter_dict
        )
        
        if self._should_fail():
            raise Exception("Vector service temporarily unavailable")
        
        # Apply filters if provided
        results = self.search_results.copy()
        if filter_dict:
            filtered_results = []
            for result in results:
                metadata = result.get("metadata", {})
                match = True
                for key, value in filter_dict.items():
                    if metadata.get(key) != value:
                        match = False
                        break
                if match:
                    filtered_results.append(result)
            results = filtered_results
        
        return results[:top_k]
    
    async def delete_vectors(
        self,
        vector_ids: List[str],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock vector deletion operation."""
        await self._simulate_delay()
        self._record_call("delete_vectors", vector_ids=vector_ids, namespace=namespace)
        
        if self._should_fail():
            raise Exception("Vector service temporarily unavailable")
        
        # Remove vectors from mock index
        deleted_count = 0
        for vector_id in vector_ids:
            if vector_id in self.index_data:
                del self.index_data[vector_id]
                deleted_count += 1
        
        return {
            "deleted_count": deleted_count,
            "namespace": namespace or "default"
        }
    
    def set_search_results(self, results: List[Dict[str, Any]]):
        """Set custom search results for testing."""
        self.search_results = results
    
    def add_search_result(self, result: Dict[str, Any]):
        """Add a search result to the mock results."""
        self.search_results.append(result)


class MockHTTPService(MockExternalService):
    """Mock HTTP service for inter-service communication testing."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.responses = {}
        self.default_response = {"status": "ok", "data": {}}
    
    async def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """Mock HTTP GET request."""
        await self._simulate_delay()
        self._record_call("get", url=url, **kwargs)
        
        if self._should_fail():
            raise Exception("HTTP service temporarily unavailable")
        
        return self.responses.get(url, self.default_response)
    
    async def post(self, url: str, data: Any = None, **kwargs) -> Dict[str, Any]:
        """Mock HTTP POST request."""
        await self._simulate_delay()
        self._record_call("post", url=url, data=data, **kwargs)
        
        if self._should_fail():
            raise Exception("HTTP service temporarily unavailable")
        
        return self.responses.get(url, self.default_response)
    
    async def put(self, url: str, data: Any = None, **kwargs) -> Dict[str, Any]:
        """Mock HTTP PUT request."""
        await self._simulate_delay()
        self._record_call("put", url=url, data=data, **kwargs)
        
        if self._should_fail():
            raise Exception("HTTP service temporarily unavailable")
        
        return self.responses.get(url, self.default_response)
    
    async def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        """Mock HTTP DELETE request."""
        await self._simulate_delay()
        self._record_call("delete", url=url, **kwargs)
        
        if self._should_fail():
            raise Exception("HTTP service temporarily unavailable")
        
        return self.responses.get(url, self.default_response)
    
    def set_response(self, url: str, response: Dict[str, Any]):
        """Set custom response for a specific URL."""
        self.responses[url] = response


def create_mock_async_context_manager(return_value: Any = None):
    """Create a mock async context manager."""
    
    class MockAsyncContextManager:
        def __init__(self, return_value):
            self.return_value = return_value
        
        async def __aenter__(self):
            return self.return_value
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    return MockAsyncContextManager(return_value)


def create_mock_async_generator(items: List[Any]):
    """Create a mock async generator."""
    
    async def mock_generator():
        for item in items:
            yield item
    
    return mock_generator()


# Convenience functions for creating common mocks
def create_llm_mock(**kwargs) -> MockLLMService:
    """Create a mock LLM service with default configuration."""
    return MockLLMService(**kwargs)


def create_vector_mock(**kwargs) -> MockVectorService:
    """Create a mock vector service with default configuration."""
    return MockVectorService(**kwargs)


def create_http_mock(**kwargs) -> MockHTTPService:
    """Create a mock HTTP service with default configuration."""
    return MockHTTPService(**kwargs)


# Pytest fixtures for common mocks
def pytest_configure_mock_fixtures():
    """Configure pytest fixtures for mock services."""
    import pytest
    
    @pytest.fixture
    def mock_llm_service():
        """Provide a mock LLM service."""
        return create_llm_mock()
    
    @pytest.fixture
    def mock_vector_service():
        """Provide a mock vector service."""
        return create_vector_mock()
    
    @pytest.fixture
    def mock_http_service():
        """Provide a mock HTTP service."""
        return create_http_mock()
    
    @pytest.fixture
    def mock_external_services(mock_llm_service, mock_vector_service, mock_http_service):
        """Provide all mock external services."""
        return {
            "llm": mock_llm_service,
            "vector": mock_vector_service,
            "http": mock_http_service
        }
    
    return {
        "mock_llm_service": mock_llm_service,
        "mock_vector_service": mock_vector_service,
        "mock_http_service": mock_http_service,
        "mock_external_services": mock_external_services,
    }