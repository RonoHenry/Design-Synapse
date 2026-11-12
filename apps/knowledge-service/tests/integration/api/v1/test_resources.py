"""Integration tests for knowledge resource API endpoints."""

from datetime import datetime

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from knowledge_service.main import app
from knowledge_service.models.resource import Resource, Topic
from sqlalchemy.orm import Session


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
        "/api/v1/bookmarks/",
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


def test_upload_pdf_file_creates_resource(client: TestClient, auth_headers):
    """Test uploading a PDF file creates a resource.

    This test should fail - endpoint doesn't exist yet.
    Following TDD RED phase - write failing test first.
    """
    # Create a mock PDF file for testing
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"

    response = client.post(
        "/api/v1/resources/upload",
        files={"file": ("test.pdf", pdf_content, "application/pdf")},
        data={
            "title": "Uploaded PDF Document",
            "description": "Test PDF upload functionality"
        },
        headers=auth_headers
    )

    # This should fail because the endpoint doesn't exist yet
    # Currently returns 404 - endpoint not found
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "Uploaded PDF Document"
    assert data["content_type"] == "pdf"
    assert data["file_size"] > 0
    assert "storage_path" in data
    assert "id" in data

def
test_upload_text_file_creates_resource(client: TestClient, auth_headers):
    """Test uploading a text file creates a resource with content extraction."""
    # Create a mock text file for testing
    text_content = "This is a test document.\n\nIt contains multiple paragraphs.\n\nThis should be extracted properly."

    response = client.post(
        "/api/v1/resources/upload",
        files={"file": ("test.txt", text_content.encode('utf-8'), "text/plain")},
        data={
            "title": "Uploaded Text Document",
            "description": "Test text upload functionality"
        },
        headers=auth_headers
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "Uploaded Text Document"
    assert data["content_type"] == "text"
    assert data["file_size"] > 0
    assert "storage_path" in data
    assert "id" in data


def test_upload_markdown_file_creates_resource(client: TestClient, auth_headers):
    """Test uploading a markdown file creates a resource with content extraction."""
    # Create a mock markdown file for testing
    markdown_content = """# Test Document

This is a test markdown document.

## Section 1

It contains multiple sections.

## Section 2

This should be extracted properly with markdown formatting preserved.
"""

    response = client.post(
        "/api/v1/resources/upload",
        files={"file": ("test.md", markdown_content.encode('utf-8'), "text/markdown")},
        data={
            "title": "Uploaded Markdown Document",
            "description": "Test markdown upload functionality"
        },
        headers=auth_headers
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "Uploaded Markdown Document"
    assert data["content_type"] == "text"
    assert data["file_size"] > 0
    assert "storage_path" in data
    assert "id" in data


def test_upload_html_file_creates_resource(client: TestClient, auth_headers):
    """Test uploading an HTML file creates a resource with content extraction."""
    # Create a mock HTML file for testing
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Test Document</title>
    <meta name="description" content="A test HTML document">
</head>
<body>
    <h1>Main Title</h1>
    <p>This is a paragraph with some content.</p>
    <h2>Subtitle</h2>
    <p>Another paragraph with more content.</p>
    <script>console.log('This should be removed');</script>
</body>
</html>"""

    response = client.post(
        "/api/v1/resources/upload",
        files={"file": ("test.html", html_content.encode('utf-8'), "text/html")},
        data={
            "title": "Uploaded HTML Document",
            "description": "Test HTML upload functionality"
        },
        headers=auth_headers
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "Uploaded HTML Document"
    assert data["content_type"] == "html"
    assert data["file_size"] > 0
    assert "storage_path" in data
    assert "id" in data


def test_upload_unsupported_file_type_fails(client: TestClient, auth_headers):
    """Test uploading an unsupported file type fails with appropriate error."""
    # Create a mock unsupported file for testing
    unsupported_content = b"This is an unsupported file type"

    response = client.post(
        "/api/v1/resources/upload",
        files={"file": ("test.xyz", unsupported_content, "application/octet-stream")},
        data={
            "title": "Unsupported File",
            "description": "This should fail"
        },
        headers=auth_headers
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "Unsupported file type" in data["detail"]


def test_preview_file_content(client: TestClient, auth_headers):
    """Test previewing file content without storing the file."""
    # Create a test text file for preview
    text_content = "This is a test document for preview functionality.\n\nIt contains multiple paragraphs.\n\nThis should be previewed properly."

    response = client.post(
        "/api/v1/resources/preview",
        files={"file": ("test.txt", text_content.encode('utf-8'), "text/plain")},
        params={"max_length": 100},
        headers=auth_headers
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["filename"] == "test.txt"
    assert data["file_extension"] == ".txt"
    assert data["file_size"] > 0
    assert data["text_length"] > 0
    assert "preview_text" in data
    assert "metadata" in data
    assert len(data["preview_text"]) <= 100  # Should be truncated to max_length


def test_validate_file_endpoint(client: TestClient, auth_headers):
    """Test file validation endpoint."""
    # Create a test text file for validation
    text_content = "This is a test document for validation."

    response = client.post(
        "/api/v1/resources/validate",
        files={"file": ("test.txt", text_content.encode('utf-8'), "text/plain")},
        headers=auth_headers
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["filename"] == "test.txt"
    assert data["file_extension"] == ".txt"
    assert data["is_supported"] == True
    assert data["content_type"] == "text"
    assert data["is_valid_size"] == True
    assert data["is_valid"] == True
    assert len(data["errors"]) == 0


def test_get_upload_config(client: TestClient, auth_headers):
    """Test getting upload configuration."""
    response = client.get("/api/v1/resources/upload/config", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "max_file_size_mb" in data
    assert "max_batch_size" in data
    assert "supported_types" in data
    assert "supported_extensions" in data
    assert "processing_config" in data

    # Check that new file types are supported
    supported_extensions = data["supported_extensions"]
    assert ".txt" in supported_extensions
    assert ".md" in supported_extensions
    assert ".html" in supported_extensions
    assert ".htm" in supported_extensions
