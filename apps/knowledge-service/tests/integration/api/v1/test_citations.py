"""Integration tests for citation endpoints."""

import pytest
from fastapi.testclient import TestClient

from knowledge_service.main import app
from knowledge_service.infrastructure.database import get_db
from tests.factories import ResourceFactory, CitationFactory, create_resource_with_citations

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


class TestCitationEndpoints:
    """Test suite for citation management."""
    
    def test_create_citation(self, db_session):
        """Test creating a new citation."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory()
        
        response = client.post(
            "/api/v1/citations",
            json={
                "resource_id": resource.id,
                "project_id": 1,
                "context": "Used in methodology section",
                "created_by": 1
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["resource_id"] == resource.id
        assert data["project_id"] == 1
        assert data["context"] == "Used in methodology section"
    
    def test_create_citation_nonexistent_resource(self, db_session):
        """Test creating citation for nonexistent resource."""
        response = client.post(
            "/api/v1/citations",
            json={
                "resource_id": 99999,
                "project_id": 1,
                "context": "Test context",
                "created_by": 1
            }
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "NOT_FOUND"
    
    def test_get_citation(self, db_session):
        """Test retrieving a citation by ID."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        CitationFactory._meta.sqlalchemy_session = db_session
        
        citation = CitationFactory()
        
        response = client.get(f"/api/v1/citations/{citation.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == citation.id
        assert data["resource_id"] == citation.resource_id
    
    def test_get_nonexistent_citation(self, db_session):
        """Test retrieving nonexistent citation."""
        response = client.get("/api/v1/citations/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "NOT_FOUND"
    
    def test_list_citations_by_project(self, db_session):
        """Test listing all citations for a project."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        CitationFactory._meta.sqlalchemy_session = db_session
        
        project_id = 1
        citation1 = CitationFactory(project_id=project_id)
        citation2 = CitationFactory(project_id=project_id)
        CitationFactory(project_id=2)  # Different project
        
        response = client.get(f"/api/v1/projects/{project_id}/citations")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(c["project_id"] == project_id for c in data)
    
    def test_list_citations_by_resource(self, db_session):
        """Test listing all citations for a resource."""
        resource = create_resource_with_citations(db_session, citation_count=3)
        
        response = client.get(f"/api/v1/resources/{resource.id}/citations")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(c["resource_id"] == resource.id for c in data)
    
    def test_update_citation(self, db_session):
        """Test updating a citation."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        CitationFactory._meta.sqlalchemy_session = db_session
        
        citation = CitationFactory(context="Original context")
        
        response = client.put(
            f"/api/v1/citations/{citation.id}",
            json={"context": "Updated context"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["context"] == "Updated context"
    
    def test_delete_citation(self, db_session):
        """Test deleting a citation."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        CitationFactory._meta.sqlalchemy_session = db_session
        
        citation = CitationFactory()
        citation_id = citation.id
        
        response = client.delete(f"/api/v1/citations/{citation_id}")
        
        assert response.status_code == 204
        
        # Verify citation is deleted
        response = client.get(f"/api/v1/citations/{citation_id}")
        assert response.status_code == 404
    
    def test_delete_nonexistent_citation(self, db_session):
        """Test deleting nonexistent citation."""
        response = client.delete("/api/v1/citations/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "NOT_FOUND"
    
    def test_citation_validation_errors(self, db_session):
        """Test citation creation with invalid data."""
        # Missing required fields
        response = client.post(
            "/api/v1/citations",
            json={"resource_id": 1}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"
    
    def test_get_citation_statistics(self, db_session):
        """Test getting citation statistics for a project."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        CitationFactory._meta.sqlalchemy_session = db_session
        
        project_id = 1
        # Create multiple citations for the same project
        for _ in range(5):
            CitationFactory(project_id=project_id)
        
        response = client.get(f"/api/v1/projects/{project_id}/citations/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_citations"] == 5
        assert data["project_id"] == project_id


class TestCitationBulkOperations:
    """Test suite for bulk citation operations."""
    
    def test_bulk_create_citations(self, db_session):
        """Test creating multiple citations at once."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        resource1 = ResourceFactory()
        resource2 = ResourceFactory()
        
        response = client.post(
            "/api/v1/citations/bulk",
            json={
                "citations": [
                    {
                        "resource_id": resource1.id,
                        "project_id": 1,
                        "context": "Context 1",
                        "created_by": 1
                    },
                    {
                        "resource_id": resource2.id,
                        "project_id": 1,
                        "context": "Context 2",
                        "created_by": 1
                    }
                ]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 2
    
    def test_bulk_delete_citations(self, db_session):
        """Test deleting multiple citations at once."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        CitationFactory._meta.sqlalchemy_session = db_session
        
        citation1 = CitationFactory()
        citation2 = CitationFactory()
        
        response = client.delete(
            "/api/v1/citations/bulk",
            json={"citation_ids": [citation1.id, citation2.id]}
        )
        
        assert response.status_code == 204
        
        # Verify citations are deleted
        assert client.get(f"/api/v1/citations/{citation1.id}").status_code == 404
        assert client.get(f"/api/v1/citations/{citation2.id}").status_code == 404
