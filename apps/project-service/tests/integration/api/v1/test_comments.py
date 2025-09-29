"""Integration tests for comment API endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from jose import jwt

from src.core.config import settings
from src.main import app


def create_test_token(user_id: int, roles: list[str] = None) -> str:
    """Create a test JWT token."""
    roles = roles or []
    token_data = {
        "sub": str(user_id),
        "roles": roles
    }
    return jwt.encode(
        token_data,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


@pytest.fixture
def auth_headers():
    """Create authorization headers with test token."""
    token = create_test_token(1)
    return {"Authorization": f"Bearer {token}"}


def test_create_comment(client: TestClient, test_project, auth_headers):
    """Test creating a new comment."""
    # Store the project ID to avoid detachment issues
    project_id = test_project.id
    
    response = client.post(
        f"/api/v1/projects/{project_id}/comments/",
        json={
            "content": "Test comment"
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["content"] == "Test comment"
    assert data["project_id"] == project_id
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_comment_invalid_project(client: TestClient, auth_headers):
    """Test creating a comment on a non-existent project."""
    response = client.post(
        "/api/v1/projects/999/comments/",
        json={
            "content": "Test comment"
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Project not found"


def test_create_reply(client: TestClient, test_project, test_comment, auth_headers):
    """Test creating a reply to a comment."""
    # Store the IDs to avoid detachment issues
    project_id = test_project.id
    comment_id = test_comment.id
    
    response = client.post(
        f"/api/v1/projects/{project_id}/comments/",
        json={
            "content": "Reply comment",
            "parent_id": comment_id
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["content"] == "Reply comment"
    assert data["parent_id"] == comment_id


def test_list_comments(client: TestClient, test_project, test_comment):
    """Test listing project comments."""
    # Store the IDs to avoid detachment issues
    project_id = test_project.id
    comment_id = test_comment.id
    
    response = client.get(f"/api/v1/projects/{project_id}/comments/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["id"] == comment_id


def test_get_comment(client: TestClient, test_project, test_comment):
    """Test getting a specific comment."""
    # Store the IDs to avoid detachment issues
    project_id = test_project.id
    comment_id = test_comment.id
    comment_content = test_comment.content
    
    response = client.get(
        f"/api/v1/projects/{project_id}/comments/{comment_id}"
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == comment_id
    assert data["content"] == comment_content


def test_update_comment(client: TestClient, test_project, test_comment, auth_headers):
    """Test updating a comment."""
    # Store the IDs to avoid detachment issues
    project_id = test_project.id
    comment_id = test_comment.id
    
    response = client.put(
        f"/api/v1/projects/{project_id}/comments/{comment_id}",
        json={
            "content": "Updated comment"
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == comment_id
    assert data["content"] == "Updated comment"


def test_delete_comment(client: TestClient, test_project, test_comment, auth_headers):
    """Test deleting a comment."""
    # Store the IDs to avoid detachment issues
    project_id = test_project.id
    comment_id = test_comment.id
    
    response = client.delete(
        f"/api/v1/projects/{project_id}/comments/{comment_id}",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify comment is deleted
    response = client.get(
        f"/api/v1/projects/{project_id}/comments/{comment_id}",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_comment_unauthorized(client: TestClient, test_project):
    """Test creating a comment without authorization."""
    response = client.post(
        f"/api/v1/projects/{test_project.id}/comments/",
        json={"content": "Test comment"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_comment_wrong_user(client: TestClient, test_project, test_comment):
    """Test updating a comment as a different user."""
    # Create token for a different user
    different_user_token = create_test_token(2)
    headers = {"Authorization": f"Bearer {different_user_token}"}
    
    response = client.put(
        f"/api/v1/projects/{test_project.id}/comments/{test_comment.id}",
        json={"content": "Updated by different user"},
        headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_comment_wrong_user(client: TestClient, test_project, test_comment):
    """Test deleting a comment as a different user."""
    # Create token for a different user
    different_user_token = create_test_token(2)
    headers = {"Authorization": f"Bearer {different_user_token}"}
    
    response = client.delete(
        f"/api/v1/projects/{test_project.id}/comments/{test_comment.id}",
        headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN