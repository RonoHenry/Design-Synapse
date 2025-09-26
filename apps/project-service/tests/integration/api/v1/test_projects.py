"""Integration tests for project API endpoints."""

import pytest
from fastapi import status


def test_create_project(client):
    """Test creating a new project."""
    response = client.post(
        "/api/v1/projects/",
        json={
            "name": "New Project",
            "description": "Project description",
            "is_public": False,
            "owner_id": 1
        }
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "New Project"
    assert data["description"] == "Project description"
    assert data["status"] == "draft"
    assert data["is_public"] is False


def test_get_project(client, test_project):
    """Test retrieving a specific project."""
    response = client.get(f"/api/v1/projects/{test_project.id}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == test_project.name
    assert data["description"] == test_project.description


def test_list_projects(client, test_projects):
    """Test listing all projects."""
    response = client.get("/api/v1/projects/")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == len(test_projects)


def test_update_project(client, test_project):
    """Test updating a project."""
    response = client.put(
        f"/api/v1/projects/{test_project.id}",
        json={
            "name": "Updated Project",
            "description": "Updated description",
            "status": "in_progress"
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated Project"
    assert data["description"] == "Updated description"
    assert data["status"] == "in_progress"


def test_delete_project(client, test_project):
    """Test deleting a project."""
    response = client.delete(f"/api/v1/projects/{test_project.id}")
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify project is deleted
    get_response = client.get(f"/api/v1/projects/{test_project.id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize("project_status", ["draft", "in_progress", "review", "completed", "archived"])
def test_update_project_status(client, test_project, project_status):
    """Test updating project status."""
    response = client.patch(
        f"/api/v1/projects/{test_project.id}/status",
        json={"status": project_status}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == project_status


def test_invalid_project_status(client, test_project):
    """Test that invalid project status is rejected."""
    response = client.patch(
        f"/api/v1/projects/{test_project.id}/status",
        json={"status": "invalid_status"}
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY