"""Integration tests for project-knowledge service interactions."""
import pytest
from sqlalchemy.orm import Session
from fastapi import status
from fastapi.testclient import TestClient

from knowledge_service.models.resource import Resource, Citation
from tests.fixtures.models import Project, User


@pytest.fixture
def test_project(db_session: Session, test_user: User):
    """Create a test project."""
    project = Project(
        name="Test Project",
        description="A test project",
        owner_id=test_user.id
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def test_resource(db_session: Session):
    """Create a test knowledge resource."""
    resource = Resource(
        title="Test Resource",
        description="A test resource",
        content_type="pdf",
        source_url="https://example.com/test",
        storage_path="/test/path.pdf"
    )
    db_session.add(resource)
    db_session.commit()
    db_session.refresh(resource)
    return resource


def test_create_project_with_knowledge_resources(
    client: TestClient,
    auth_headers: dict,
    test_resource: Resource
):
    """Test creating a project with linked knowledge resources."""
    response = client.post(
        "/api/v1/projects/",
        headers=auth_headers,
        json={
            "name": "New Project",
            "description": "Project with knowledge resources",
            "knowledge_resource_ids": [test_resource.id]
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "knowledge_resources" in data
    assert len(data["knowledge_resources"]) == 1
    assert data["knowledge_resources"][0]["id"] == test_resource.id


def test_add_citation_to_project(
    client: TestClient,
    auth_headers: dict,
    test_project: Project,
    test_resource: Resource
):
    """Test adding a citation to a project."""
    response = client.post(
        f"/api/v1/knowledge/citations/",
        headers=auth_headers,
        json={
            "resource_id": test_resource.id,
            "project_id": test_project.id,
            "context": "Used in project documentation",
            "page_number": 1
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["resource_id"] == test_resource.id
    assert data["project_id"] == test_project.id


def test_get_project_knowledge_resources(
    client: TestClient,
    auth_headers: dict,
    test_project: Project,
    test_resource: Resource,
    db_session: Session
):
    """Test retrieving knowledge resources linked to a project."""
    # Create citation linking resource to project
    citation = Citation(
        resource_id=test_resource.id,
        project_id=test_project.id,
        context="Test citation"
    )
    db_session.add(citation)
    db_session.commit()

    response = client.get(
        f"/api/v1/projects/{test_project.id}/knowledge-resources",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == test_resource.id


def test_search_project_specific_knowledge(
    client: TestClient,
    auth_headers: dict,
    test_project: Project,
    test_resource: Resource
):
    """Test searching knowledge resources within project context."""
    response = client.get(
        f"/api/v1/projects/{test_project.id}/knowledge-search",
        headers=auth_headers,
        params={"query": "test", "include_global": True}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data["results"], list)
    assert "project_resources" in data
    assert "global_resources" in data


def test_project_knowledge_recommendations(
    client: TestClient,
    auth_headers: dict,
    test_project: Project,
    test_resource: Resource
):
    """Test getting knowledge resource recommendations for a project."""
    response = client.get(
        f"/api/v1/projects/{test_project.id}/knowledge-recommendations",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert "relevance_score" in data[0]


def test_project_citation_analytics(
    client: TestClient,
    auth_headers: dict,
    test_project: Project,
    test_resource: Resource,
    db_session: Session
):
    """Test retrieving citation analytics for a project."""
    # Add multiple citations
    for i in range(3):
        citation = Citation(
            resource_id=test_resource.id,
            project_id=test_project.id,
            context=f"Citation {i}"
        )
        db_session.add(citation)
    db_session.commit()

    response = client.get(
        f"/api/v1/projects/{test_project.id}/citation-analytics",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_citations" in data
    assert data["total_citations"] == 3
    assert "resource_breakdown" in data


def test_sync_project_knowledge_resources(
    client: TestClient,
    auth_headers: dict,
    test_project: Project,
    test_resource: Resource
):
    """Test syncing knowledge resources with a project."""
    response = client.put(
        f"/api/v1/projects/{test_project.id}/knowledge-resources",
        headers=auth_headers,
        json={
            "resource_ids": [test_resource.id]
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["knowledge_resources"]) == 1


def test_project_knowledge_export(
    client: TestClient,
    auth_headers: dict,
    test_project: Project,
    test_resource: Resource
):
    """Test exporting project knowledge resources."""
    response = client.get(
        f"/api/v1/projects/{test_project.id}/knowledge-export",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "resources" in data
    assert "citations" in data