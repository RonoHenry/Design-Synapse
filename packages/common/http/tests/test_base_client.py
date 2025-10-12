"""Tests for base HTTP client."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx
from common.http.base_client import BaseHTTPClient, CircuitBreakerState


@pytest.fixture
def base_client():
    """Create a base HTTP client for testing."""
    return BaseHTTPClient(
        base_url="http://test-service:8000",
        timeout=5.0,
        max_retries=3
    )


@pytest.mark.asyncio
async def test_client_initialization(base_client):
    """Test client initializes with correct configuration."""
    assert base_client.base_url == "http://test-service:8000"
    assert base_client.timeout == 5.0
    assert base_client.max_retries == 3
    assert base_client.circuit_breaker_state == CircuitBreakerState.CLOSED


@pytest.mark.asyncio
async def test_successful_get_request(base_client):
    """Test successful GET request."""
    with patch.object(base_client._client, 'get', new_callable=AsyncMock) as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response
        
        result = await base_client.get("/test")
        
        assert result == {"data": "test"}
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_retry_on_transient_failure(base_client):
    """Test retry mechanism on transient failures."""
    with patch.object(base_client._client, 'get', new_callable=AsyncMock) as mock_get:
        # First two calls fail, third succeeds
        mock_get.side_effect = [
            httpx.TimeoutException("Timeout"),
            httpx.TimeoutException("Timeout"),
            Mock(status_code=200, json=lambda: {"data": "success"})
        ]
        
        result = await base_client.get("/test")
        
        assert result == {"data": "success"}
        assert mock_get.call_count == 3


@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures(base_client):
    """Test circuit breaker opens after threshold failures."""
    base_client.circuit_breaker_threshold = 2
    
    with patch.object(base_client._client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=Mock(),
            response=Mock(status_code=500)
        )
        
        # First two requests should fail and open circuit
        with pytest.raises(Exception):
            await base_client.get("/test")
        
        with pytest.raises(Exception):
            await base_client.get("/test")
        
        # Circuit should now be open
        assert base_client.circuit_breaker_state == CircuitBreakerState.OPEN
        
        # Next request should fail immediately without calling the service
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await base_client.get("/test")


@pytest.mark.asyncio
async def test_exponential_backoff(base_client):
    """Test exponential backoff between retries."""
    with patch.object(base_client._client, 'get', new_callable=AsyncMock) as mock_get:
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            mock_get.side_effect = [
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                Mock(status_code=200, json=lambda: {"data": "success"})
            ]
            
            await base_client.get("/test")
            
            # Should have slept with exponential backoff
            assert mock_sleep.call_count == 2
            # First retry: 1 second, second retry: 2 seconds
            calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert calls[0] == 1
            assert calls[1] == 2


@pytest.mark.asyncio
async def test_post_request_with_data(base_client):
    """Test POST request with JSON data."""
    with patch.object(base_client._client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 1, "created": True}
        mock_post.return_value = mock_response
        
        result = await base_client.post("/test", json={"name": "test"})
        
        assert result == {"id": 1, "created": True}
        mock_post.assert_called_once_with(
            "http://test-service:8000/test",
            json={"name": "test"},
            timeout=5.0
        )


@pytest.mark.asyncio
async def test_request_logging(base_client):
    """Test request and response logging."""
    with patch.object(base_client._client, 'get', new_callable=AsyncMock) as mock_get:
        with patch('logging.Logger.info') as mock_log:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}
            mock_get.return_value = mock_response
            
            await base_client.get("/test")
            
            # Should log request and response
            assert mock_log.call_count >= 2
