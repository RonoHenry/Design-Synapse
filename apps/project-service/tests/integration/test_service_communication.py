"""Integration tests for service-to-service communication using HTTP clients."""

# Add packages to path
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

packages_path = Path(__file__).parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.http.base_client import BaseHTTPClient
from common.http.clients import KnowledgeServiceClient, UserServiceClient


class TestServiceCommunication:
    """Test service-to-service communication patterns."""

    @pytest.fixture
    def user_service_client(self):
        """Create a user service client for testing."""
        return UserServiceClient(base_url="http://user-service:8000", timeout=5.0)

    @pytest.fixture
    def knowledge_service_client(self):
        """Create a knowledge service client for testing."""
        return KnowledgeServiceClient(
            base_url="http://knowledge-service:8000", timeout=5.0
        )

    @pytest.mark.asyncio
    async def test_user_service_get_user_success(self, user_service_client):
        """Test successful user retrieval from user service."""
        with patch.object(
            user_service_client._client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": 1,
                "username": "testuser",
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
            }
            mock_get.return_value = mock_response

            user = await user_service_client.get_user(1)

            assert user["id"] == 1
            assert user["username"] == "testuser"
            assert user["email"] == "test@example.com"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_service_get_user_not_found(self, user_service_client):
        """Test user not found from user service."""
        with patch.object(
            user_service_client._client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            mock_get.side_effect = httpx.HTTPStatusError(
                "Not Found", request=Mock(), response=mock_response
            )

            with pytest.raises(httpx.HTTPStatusError):
                await user_service_client.get_user(999)

    @pytest.mark.asyncio
    async def test_user_service_validate_user_success(self, user_service_client):
        """Test successful user validation from user service."""
        with patch.object(
            user_service_client._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "valid": True,
                "user_id": 1,
                "username": "testuser",
            }
            mock_post.return_value = mock_response

            result = await user_service_client.validate_user("valid_token")

            assert result["valid"] is True
            assert result["user_id"] == 1
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_service_validate_user_invalid_token(self, user_service_client):
        """Test invalid token validation from user service."""
        with patch.object(
            user_service_client._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_post.return_value = mock_response
            mock_post.side_effect = httpx.HTTPStatusError(
                "Unauthorized", request=Mock(), response=mock_response
            )

            with pytest.raises(httpx.HTTPStatusError):
                await user_service_client.validate_user("invalid_token")

    @pytest.mark.asyncio
    async def test_knowledge_service_search_resources_success(
        self, knowledge_service_client
    ):
        """Test successful resource search from knowledge service."""
        with patch.object(
            knowledge_service_client._client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {
                        "id": 1,
                        "title": "Test Resource",
                        "description": "A test resource",
                        "content_type": "pdf",
                    }
                ],
                "total": 1,
                "page": 1,
                "per_page": 10,
            }
            mock_get.return_value = mock_response

            results = await knowledge_service_client.search_resources("test query")

            assert len(results["results"]) == 1
            assert results["results"][0]["title"] == "Test Resource"
            assert results["total"] == 1
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_knowledge_service_create_citation_success(
        self, knowledge_service_client
    ):
        """Test successful citation creation in knowledge service."""
        with patch.object(
            knowledge_service_client._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                "id": 1,
                "resource_id": 1,
                "project_id": 1,
                "context": "This is a citation context",
                "created_by": 1,
            }
            mock_post.return_value = mock_response

            citation_data = {
                "resource_id": 1,
                "project_id": 1,
                "context": "This is a citation context",
                "created_by": 1,
            }

            citation = await knowledge_service_client.create_citation(citation_data)

            assert citation["id"] == 1
            assert citation["resource_id"] == 1
            assert citation["project_id"] == 1
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_communication_with_retry(self, user_service_client):
        """Test service communication with retry mechanism."""
        with patch.object(
            user_service_client._client, "get", new_callable=AsyncMock
        ) as mock_get:
            # First call fails, second succeeds
            mock_get.side_effect = [
                httpx.TimeoutException("Timeout"),
                Mock(status_code=200, json=lambda: {"id": 1, "username": "testuser"}),
            ]

            user = await user_service_client.get_user(1)

            assert user["id"] == 1
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_service_communication_circuit_breaker(self, user_service_client):
        """Test circuit breaker functionality in service communication."""
        user_service_client.circuit_breaker_threshold = 2

        with patch.object(
            user_service_client._client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "Server Error", request=Mock(), response=Mock(status_code=500)
            )

            # First two requests should fail and open circuit
            with pytest.raises(Exception):
                await user_service_client.get_user(1)

            with pytest.raises(Exception):
                await user_service_client.get_user(1)

            # Third request should fail immediately due to open circuit
            with pytest.raises(Exception, match="Circuit breaker is OPEN"):
                await user_service_client.get_user(1)

    @pytest.mark.asyncio
    async def test_cross_service_workflow_project_with_resources(
        self, user_service_client, knowledge_service_client
    ):
        """Test cross-service workflow: project creation with resource addition."""
        # Mock user validation
        with patch.object(
            user_service_client._client, "post", new_callable=AsyncMock
        ) as mock_user_post:
            mock_user_post.return_value = Mock(
                status_code=200,
                json=lambda: {"valid": True, "user_id": 1, "username": "testuser"},
            )

            # Mock resource search
            with patch.object(
                knowledge_service_client._client, "get", new_callable=AsyncMock
            ) as mock_knowledge_get:
                mock_knowledge_get.return_value = Mock(
                    status_code=200,
                    json=lambda: {
                        "results": [{"id": 1, "title": "Relevant Resource"}],
                        "total": 1,
                    },
                )

                # Mock citation creation
                with patch.object(
                    knowledge_service_client._client, "post", new_callable=AsyncMock
                ) as mock_knowledge_post:
                    mock_knowledge_post.return_value = Mock(
                        status_code=201,
                        json=lambda: {
                            "id": 1,
                            "resource_id": 1,
                            "project_id": 1,
                            "context": "Added to project",
                        },
                    )

                    # Simulate workflow
                    user_validation = await user_service_client.validate_user("token")
                    assert user_validation["valid"] is True

                    resources = await knowledge_service_client.search_resources(
                        "project topic"
                    )
                    assert len(resources["results"]) == 1

                    citation = await knowledge_service_client.create_citation(
                        {
                            "resource_id": resources["results"][0]["id"],
                            "project_id": 1,
                            "context": "Added to project",
                            "created_by": user_validation["user_id"],
                        }
                    )
                    assert citation["id"] == 1

    @pytest.mark.asyncio
    async def test_service_communication_error_handling(self, user_service_client):
        """Test error handling in service communication."""
        with patch.object(
            user_service_client._client, "get", new_callable=AsyncMock
        ) as mock_get:
            # Test different error scenarios
            error_scenarios = [
                httpx.TimeoutException("Request timeout"),
                httpx.ConnectError("Connection failed"),
                httpx.HTTPStatusError(
                    "Server Error", request=Mock(), response=Mock(status_code=500)
                ),
            ]

            for error in error_scenarios:
                mock_get.side_effect = error

                with pytest.raises(Exception):
                    await user_service_client.get_user(1)

    @pytest.mark.asyncio
    async def test_service_communication_request_logging(self, user_service_client):
        """Test request logging in service communication."""
        with patch.object(
            user_service_client._client, "get", new_callable=AsyncMock
        ) as mock_get:
            with patch("logging.Logger.info") as mock_log:
                mock_get.return_value = Mock(
                    status_code=200, json=lambda: {"id": 1, "username": "testuser"}
                )

                await user_service_client.get_user(1)

                # Should log request and response
                assert mock_log.call_count >= 1
