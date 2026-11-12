"""Tests for typed service clients."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from unittest.mock import AsyncMock, patch
from common.http.clients import UserServiceClient, ProjectServiceClient, KnowledgeServiceClient


@pytest.mark.asyncio
async def test_user_service_client_get_user():
    """Test UserServiceClient get_user method."""
    client = UserServiceClient()
    
    with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"id": 1, "email": "test@example.com"}
        
        user = await client.get_user(user_id=1)
        
        assert user["id"] == 1
        assert user["email"] == "test@example.com"
        mock_get.assert_called_once_with("/users/1")


@pytest.mark.asyncio
async def test_user_service_client_create_user():
    """Test UserServiceClient create_user method."""
    client = UserServiceClient()
    
    with patch.object(client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = {"id": 1, "email": "new@example.com"}
        
        user_data = {"email": "new@example.com", "password": "secure"}
        user = await client.create_user(user_data)
        
        assert user["id"] == 1
        mock_post.assert_called_once_with("/users", json=user_data)


@pytest.mark.asyncio
async def test_user_service_client_authenticate():
    """Test UserServiceClient authenticate method."""
    client = UserServiceClient()
    
    with patch.object(client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = {"access_token": "token123", "user_id": 1}
        
        auth_data = await client.authenticate("test@example.com", "password")
        
        assert auth_data["access_token"] == "token123"
        mock_post.assert_called_once_with(
            "/auth/login",
            json={"email": "test@example.com", "password": "password"}
        )


@pytest.mark.asyncio
async def test_project_service_client_get_project():
    """Test ProjectServiceClient get_project method."""
    client = ProjectServiceClient()
    
    with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"id": 1, "name": "Test Project"}
        
        project = await client.get_project(project_id=1)
        
        assert project["id"] == 1
        assert project["name"] == "Test Project"
        mock_get.assert_called_once_with("/projects/1")


@pytest.mark.asyncio
async def test_project_service_client_list_projects():
    """Test ProjectServiceClient list_projects method."""
    client = ProjectServiceClient()
    
    with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [{"id": 1}, {"id": 2}]
        
        projects = await client.list_projects(skip=0, limit=10)
        
        assert len(projects) == 2
        mock_get.assert_called_once_with("/projects?skip=0&limit=10")


@pytest.mark.asyncio
async def test_project_service_client_create_comment():
    """Test ProjectServiceClient create_comment method."""
    client = ProjectServiceClient()
    
    with patch.object(client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = {"id": 1, "content": "Great!"}
        
        comment_data = {"content": "Great!"}
        comment = await client.create_comment(project_id=1, comment_data=comment_data)
        
        assert comment["id"] == 1
        mock_post.assert_called_once_with("/projects/1/comments", json=comment_data)


@pytest.mark.asyncio
async def test_knowledge_service_client_search_resources():
    """Test KnowledgeServiceClient search_resources method."""
    client = KnowledgeServiceClient()
    
    with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"results": [{"id": 1, "title": "Resource 1"}]}
        
        results = await client.search_resources(query="test", resource_type="pdf", limit=20)
        
        assert "results" in results
        mock_get.assert_called_once()
        call_args = mock_get.call_args[0][0]
        assert "/search?" in call_args
        assert "query=test" in call_args
        assert "resource_type=pdf" in call_args


@pytest.mark.asyncio
async def test_knowledge_service_client_create_citation():
    """Test KnowledgeServiceClient create_citation method."""
    client = KnowledgeServiceClient()
    
    with patch.object(client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = {"id": 1, "resource_id": 1, "project_id": 1}
        
        citation = await client.create_citation(
            resource_id=1,
            project_id=1,
            context="Used for design"
        )
        
        assert citation["id"] == 1
        mock_post.assert_called_once_with(
            "/citations",
            json={"resource_id": 1, "project_id": 1, "context": "Used for design"}
        )
