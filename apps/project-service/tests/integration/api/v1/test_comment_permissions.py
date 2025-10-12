"""Integration tests for comment permissions."""

from fastapi import status
from fastapi.testclient import TestClient
from jose import jwt
from src.core.config import settings
from src.main import app


def create_test_token(user_id: int, roles: list[str] = None) -> str:
    """Create a test JWT token."""
    roles = roles or []
    token_data = {"sub": str(user_id), "roles": roles}
    return jwt.encode(
        token_data, settings.jwt.secret_key, algorithm=settings.jwt.algorithm
    )


def test_create_comment_unauthorized(client: TestClient, test_project):
    """Test creating a comment without authentication."""
    response = client.post(
        f"/projects/{test_project['id']}/comments/", json={"content": "Test comment"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_own_comment(client: TestClient, test_project, auth_headers):
    """Test updating user's own comment."""
    # Create a comment first
    create_response = client.post(
        f"/projects/{test_project['id']}/comments/",
        json={"content": "Original comment"},
        headers=auth_headers,
    )
    comment_id = create_response.json()["id"]

    # Update the comment
    response = client.put(
        f"/projects/{test_project['id']}/comments/{comment_id}",
        json={"content": "Updated comment"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["content"] == "Updated comment"


def test_update_others_comment(client: TestClient, test_project):
    """Test updating someone else's comment."""
    # Create a comment with user 1
    headers_user1 = {"Authorization": f"Bearer {create_test_token(1)}"}
    create_response = client.post(
        f"/projects/{test_project['id']}/comments/",
        json={"content": "Original comment"},
        headers=headers_user1,
    )
    comment_id = create_response.json()["id"]

    # Try to update with user 2
    headers_user2 = {"Authorization": f"Bearer {create_test_token(2)}"}
    response = client.put(
        f"/projects/{test_project['id']}/comments/{comment_id}",
        json={"content": "Updated by other user"},
        headers=headers_user2,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_update_comment(client: TestClient, test_project):
    """Test admin updating any comment."""
    # Create a comment with regular user
    headers_user = {"Authorization": f"Bearer {create_test_token(1)}"}
    create_response = client.post(
        f"/projects/{test_project['id']}/comments/",
        json={"content": "Original comment"},
        headers=headers_user,
    )
    comment_id = create_response.json()["id"]

    # Update with admin user
    headers_admin = {"Authorization": f"Bearer {create_test_token(2, roles=['admin'])}"}
    response = client.put(
        f"/projects/{test_project['id']}/comments/{comment_id}",
        json={"content": "Updated by admin"},
        headers=headers_admin,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["content"] == "Updated by admin"


def test_project_owner_delete_comment(client: TestClient, test_project):
    """Test project owner deleting any comment in their project."""
    # Create a comment with user 2
    headers_user2 = {"Authorization": f"Bearer {create_test_token(2)}"}
    create_response = client.post(
        f"/projects/{test_project['id']}/comments/",
        json={"content": "Comment to delete"},
        headers=headers_user2,
    )
    comment_id = create_response.json()["id"]

    # Delete with project owner (user 1)
    headers_owner = {
        "Authorization": f"Bearer {create_test_token(1)}"
    }  # Assuming project owner is user 1
    response = client.delete(
        f"/projects/{test_project['id']}/comments/{comment_id}", headers=headers_owner
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
