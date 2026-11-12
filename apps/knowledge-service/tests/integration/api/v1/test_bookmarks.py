"""Integration tests for bookmark endpoints."""

import pytest
from fastapi.testclient import TestClient
from knowledge_service.infrastructure.database import get_db
from knowledge_service.main import app

from tests.factories import BookmarkFactory, ResourceFactory

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_dependency(db_session):
    """Override the get_db dependency with our test session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


class TestBookmarkEndpoints:
    """Test suite for bookmark management."""

    def test_create_bookmark(self, db_session):
        """Test creating a new bookmark."""
        ResourceFactory._meta.sqlalchemy_session = db_session

        resource = ResourceFactory()

        response = client.post(
            "/api/v1/bookmarks/",
            json={
                "resource_id": resource.id,
                "notes": "Important resource for my project",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["resource_id"] == resource.id
        assert data["user_id"] == 1  # Mock user ID
        assert data["notes"] == "Important resource for my project"
        assert "created_at" in data

    def test_create_bookmark_nonexistent_resource(self, db_session):
        """Test creating bookmark for nonexistent resource."""
        response = client.post(
            "/api/v1/bookmarks/", json={"resource_id": 99999, "notes": "Test notes"}
        )

        assert response.status_code == 404
        data = response.json()
        assert "Resource not found" in data["detail"]

    def test_create_duplicate_bookmark(self, db_session):
        """Test creating duplicate bookmark for same resource."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session

        resource = ResourceFactory()
        BookmarkFactory(resource_id=resource.id, user_id=1)

        response = client.post(
            "/api/v1/bookmarks/",
            json={"resource_id": resource.id, "notes": "Duplicate bookmark"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "already bookmarked" in data["detail"]

    def test_list_bookmarks(self, db_session):
        """Test listing user's bookmarks."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session

        # Create bookmarks for current user
        resource1 = ResourceFactory()
        resource2 = ResourceFactory()
        bookmark1 = BookmarkFactory(resource_id=resource1.id, user_id=1)
        bookmark2 = BookmarkFactory(resource_id=resource2.id, user_id=1)

        # Create bookmark for different user
        resource3 = ResourceFactory()
        BookmarkFactory(resource_id=resource3.id, user_id=2)

        response = client.get("/api/v1/bookmarks/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert all(item["user_id"] == 1 for item in data["items"])

    def test_list_bookmarks_pagination(self, db_session):
        """Test bookmark listing with pagination."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session

        # Create multiple bookmarks
        for i in range(5):
            resource = ResourceFactory()
            BookmarkFactory(resource_id=resource.id, user_id=1)

        response = client.get("/api/v1/bookmarks/?page=1&limit=3")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["limit"] == 3
        assert len(data["items"]) == 3

    def test_list_bookmarks_filter_by_resource(self, db_session):
        """Test filtering bookmarks by resource ID."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session

        resource1 = ResourceFactory()
        resource2 = ResourceFactory()
        BookmarkFactory(resource_id=resource1.id, user_id=1)
        BookmarkFactory(resource_id=resource2.id, user_id=1)

        response = client.get(f"/api/v1/bookmarks/?resource_id={resource1.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["resource_id"] == resource1.id

    def test_get_bookmark(self, db_session):
        """Test retrieving a specific bookmark."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session

        resource = ResourceFactory()
        bookmark = BookmarkFactory(resource_id=resource.id, user_id=1)

        response = client.get(f"/api/v1/bookmarks/{bookmark.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == bookmark.id
        assert data["resource_id"] == resource.id
        assert data["user_id"] == 1

    def test_get_bookmark_not_found(self, db_session):
        """Test retrieving nonexistent bookmark."""
        response = client.get("/api/v1/bookmarks/99999")

        assert response.status_code == 404
        data = response.json()
        assert "Bookmark not found" in data["detail"]

    def test_get_bookmark_different_user(self, db_session):
        """Test retrieving bookmark belonging to different user."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session

        resource = ResourceFactory()
        bookmark = BookmarkFactory(resource_id=resource.id, user_id=2)  # Different user

        response = client.get(f"/api/v1/bookmarks/{bookmark.id}")

        assert response.status_code == 404
        data = response.json()
        assert "Bookmark not found" in data["detail"]

    def test_update_bookmark(self, db_session):
        """Test updating bookmark notes."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session

        resource = ResourceFactory()
        bookmark = BookmarkFactory(
            resource_id=resource.id, user_id=1, notes="Original notes"
        )

        response = client.put(
            f"/api/v1/bookmarks/{bookmark.id}", json={"notes": "Updated notes"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Updated notes"

    def test_update_bookmark_not_found(self, db_session):
        """Test updating nonexistent bookmark."""
        response = client.put(
            "/api/v1/bookmarks/99999", json={"notes": "Updated notes"}
        )

        assert response.status_code == 404
        data = response.json()
        assert "Bookmark not found" in data["detail"]

    def test_delete_bookmark(self, db_session):
        """Test deleting a bookmark."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session

        resource = ResourceFactory()
        bookmark = BookmarkFactory(resource_id=resource.id, user_id=1)
        bookmark_id = bookmark.id

        response = client.delete(f"/api/v1/bookmarks/{bookmark_id}")

        assert response.status_code == 204

        # Verify bookmark is deleted
        response = client.get(f"/api/v1/bookmarks/{bookmark_id}")
        assert response.status_code == 404

    def test_delete_bookmark_not_found(self, db_session):
        """Test deleting nonexistent bookmark."""
        response = client.delete("/api/v1/bookmarks/99999")

        assert response.status_code == 404
        data = response.json()
        assert "Bookmark not found" in data["detail"]

    def test_get_bookmark_by_resource(self, db_session):
        """Test getting bookmark by resource ID."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session

        resource = ResourceFactory()
        bookmark = BookmarkFactory(resource_id=resource.id, user_id=1)

        response = client.get(f"/api/v1/bookmarks/resource/{resource.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == bookmark.id
        assert data["resource_id"] == resource.id

    def test_get_bookmark_by_resource_not_found(self, db_session):
        """Test getting bookmark for resource that's not bookmarked."""
        ResourceFactory._meta.sqlalchemy_session = db_session

        resource = ResourceFactory()

        response = client.get(f"/api/v1/bookmarks/resource/{resource.id}")

        assert response.status_code == 404
        data = response.json()
        assert "Bookmark not found" in data["detail"]

    def test_bulk_delete_bookmarks(self, db_session):
        """Test bulk deleting bookmarks."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session

        resource1 = ResourceFactory()
        resource2 = ResourceFactory()
        bookmark1 = BookmarkFactory(resource_id=resource1.id, user_id=1)
        bookmark2 = BookmarkFactory(resource_id=resource2.id, user_id=1)

        response = client.post(
            "/api/v1/bookmarks/bulk-delete",
            json={"bookmark_ids": [bookmark1.id, bookmark2.id]},
        )

        assert response.status_code == 204

        # Verify bookmarks are deleted
        assert client.get(f"/api/v1/bookmarks/{bookmark1.id}").status_code == 404
        assert client.get(f"/api/v1/bookmarks/{bookmark2.id}").status_code == 404

    def test_bulk_delete_invalid_data(self, db_session):
        """Test bulk delete with invalid data."""
        response = client.post(
            "/api/v1/bookmarks/bulk-delete", json={"bookmark_ids": "invalid"}
        )

        assert response.status_code == 422

    def test_bulk_delete_nonexistent_bookmarks(self, db_session):
        """Test bulk delete with nonexistent bookmark IDs."""
        response = client.post(
            "/api/v1/bookmarks/bulk-delete", json={"bookmark_ids": [99999, 99998]}
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]


class TestBookmarkValidation:
    """Test suite for bookmark validation."""

    def test_create_bookmark_missing_resource_id(self, db_session):
        """Test creating bookmark without resource ID."""
        response = client.post("/api/v1/bookmarks/", json={"notes": "Test notes"})

        assert response.status_code == 422
        data = response.json()
        assert "Resource ID is required" in data["detail"]

    def test_create_bookmark_with_empty_notes(self, db_session):
        """Test creating bookmark with empty notes."""
        ResourceFactory._meta.sqlalchemy_session = db_session

        resource = ResourceFactory()

        response = client.post(
            "/api/v1/bookmarks/", json={"resource_id": resource.id, "notes": ""}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["notes"] == ""

    def test_create_bookmark_without_notes(self, db_session):
        """Test creating bookmark without notes field."""
        ResourceFactory._meta.sqlalchemy_session = db_session

        resource = ResourceFactory()

        response = client.post("/api/v1/bookmarks/", json={"resource_id": resource.id})

        assert response.status_code == 201
        data = response.json()
        assert data["notes"] is None


class TestBookmarkSorting:
    """Test suite for bookmark sorting and ordering."""

    def test_bookmarks_ordered_by_creation_date(self, db_session):
        """Test that bookmarks are ordered by creation date (newest first)."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session

        # Create bookmarks with different timestamps
        import time

        resource1 = ResourceFactory()
        bookmark1 = BookmarkFactory(resource_id=resource1.id, user_id=1)

        time.sleep(0.1)  # Small delay to ensure different timestamps

        resource2 = ResourceFactory()
        bookmark2 = BookmarkFactory(resource_id=resource2.id, user_id=1)

        response = client.get("/api/v1/bookmarks/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

        # Newer bookmark should be first
        assert data["items"][0]["id"] == bookmark2.id
        assert data["items"][1]["id"] == bookmark1.id
