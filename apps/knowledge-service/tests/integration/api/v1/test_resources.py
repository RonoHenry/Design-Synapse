"""Integration tests for knowledge resource API endpoints."""

from datetime import datetime
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from knowledge_service.models.resource import Resource, Topic
from knowledge_service.main import app


@pytest.fixture
def auth_headers():
    """Create authorization headers for testing."""
    return {"Authorization": "Bearer 1"} # Use user ID 1 for testing


@pytest.fixture
def test_topic(db_session: Session):
    """Create a test topic."""
    topic = Topic(
        name="Test Topic",
        description="Topic for testing"
    )
    db_session.add(topic)
    db_session.commit()
    db_session.refresh(topic)
    return topic


@pytest.fixture
def test_resource(db_session: Session, test_topic: Topic):
    """Create a test resource."""
    resource = Resource(
        title="Test Resource",
        description="Resource for testing",
        content_type="pdf",
        source_url="https://example.com/test",
        source_platform="Test Platform",
        author="Test Author",
        publication_date=datetime.utcnow(),
        license_type="MIT",
        storage_path="/test/path.pdf",
        file_size=1024,
        topics=[test_topic]
    )
    db_session.add(resource)
    db_session.commit()
    db_session.refresh(resource)
    return resource


def test_create_topic(client: TestClient, auth_headers):
    """Test creating a new topic."""
    response = client.post(
        "/api/v1/resources/topics/?name=Architecture&description=Architectural+principles",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Architecture"
    assert data["description"] == "Architectural principles"
    assert "id" in data


def test_create_duplicate_topic(client: TestClient, test_topic, auth_headers):
    """Test creating a topic with duplicate name."""
    response = client.post(
        f"/api/v1/resources/topics/?name={test_topic.name}&description=Different+description",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_list_topics(client: TestClient, test_topic, auth_headers):
    """Test listing topics."""
    response = client.get("/api/v1/resources/topics", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(topic["name"] == test_topic.name for topic in data)


def test_get_topic(client: TestClient, test_topic, auth_headers):
    """Test getting a specific topic."""
    response = client.get(f"/api/v1/resources/topics/{test_topic.id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == test_topic.name
    assert data["description"] == test_topic.description


def test_update_topic(client: TestClient, test_topic, auth_headers):
    """Test updating a topic."""
    response = client.put(
        f"/api/v1/resources/topics/{test_topic.id}?name=Updated+Topic&description=Updated+description",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated Topic"
    assert data["description"] == "Updated description"


def test_create_resource(client: TestClient, test_topic, auth_headers):
    """Test creating a new resource."""
    response = client.post(
        "/api/v1/resources",
        json={
            "title": "New Resource",
            "description": "Test description",
            "content_type": "pdf",
            "source_url": "https://example.com/new",
            "source_platform": "Example",
            "author": "Test Author",
            "storage_path": "/test/new.pdf",
            "file_size": 1024,
            "topic_ids": [test_topic.id]
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "New Resource"
    assert data["storage_path"] == "/test/new.pdf"
    assert len(data["topics"]) == 1
    assert data["topics"][0]["id"] == test_topic.id


def test_list_resources(client: TestClient, test_resource, auth_headers):
    """Test listing resources."""
    response = client.get("/api/v1/resources/", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert len(data["items"]) >= 1
    assert any(resource["title"] == test_resource.title for resource in data["items"])


def test_search_resources(client: TestClient, test_resource, auth_headers):
    """Test searching resources."""
    response = client.get(
        "/api/v1/search/global",
        params={"query": "test", "page_size": 10},
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, dict)
    # Note: actual results depend on vector search implementation


def test_create_bookmark(client: TestClient, test_resource, auth_headers):
    """Test creating a bookmark."""
    response = client.post(
        "/api/v1/resources/bookmarks",
        json={
            "resource_id": test_resource.id,
            "notes": "Important resource"
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["resource_id"] == test_resource.id
    assert data["notes"] == "Important resource"


def test_create_citation(client: TestClient, test_resource, auth_headers):
    """Test creating a citation."""
    response = client.post(
        "/api/v1/citations/",
        json={
            "resource_id": test_resource.id,
            "project_id": 1,
            "context": "Used in calculations"
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["resource_id"] == test_resource.id
    assert data["context"] == "Used in calculations"


def test_create_resource_invalid_topic(client: TestClient, auth_headers):
    """Test creating a resource with invalid topic ID."""
    response = client.post(
        "/api/v1/resources",
        json={
            "title": "Invalid Resource",
            "description": "Test description",
            "content_type": "pdf",
            "source_url": "https://example.com/invalid",
            "source_platform": "Example",
            "storage_path": "/test/path.pdf",
            "topic_ids": [999999]
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_bookmark_invalid_resource(client: TestClient, auth_headers):
    """Test creating a bookmark for non-existent resource."""
    response = client.post(
        "/api/v1/resources/bookmarks",
        json={
            "resource_id": 999999,
            "notes": "Invalid resource"
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_resource_unauthorized(client: TestClient, test_topic):
    """Test creating a resource without authorization."""
    response = client.post(
        "/api/v1/resources/",
        json={
            "title": "Unauthorized Resource",
            "description": "Test description",
            "content_type": "pdf",
            "source_url": "https://example.com/unauthorized",
            "source_platform": "Example",
            "license_type": "MIT",
            "topic_ids": [test_topic.id]
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED