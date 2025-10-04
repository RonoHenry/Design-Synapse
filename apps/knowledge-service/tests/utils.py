"""Shared test utilities for project-knowledge integration tests."""
from typing import Dict, Any
from sqlalchemy.orm import Session

from apps.project_service.src.models.project import Project
from apps.project_service.src.models.user import User
from knowledge_service.models.resource import Resource, Citation, Topic


def create_test_project_with_resources(
    db_session: Session,
    user: User,
    resources: list[Resource] = None
) -> Project:
    """Create a test project with optional knowledge resources."""
    project = Project(
        name="Test Project",
        description="A test project with resources",
        owner_id=user.id
    )
    db_session.add(project)
    db_session.commit()

    if resources:
        for resource in resources:
            citation = Citation(
                resource_id=resource.id,
                project_id=project.id,
                context="Test citation"
            )
            db_session.add(citation)
        db_session.commit()
    
    return project


def create_test_resource_with_topics(
    db_session: Session,
    topics: list[str] = None
) -> Resource:
    """Create a test resource with optional topics."""
    # Create topics if provided
    topic_objects = []
    if topics:
        for topic_name in topics:
            topic = Topic(name=topic_name, description=f"Description for {topic_name}")
            db_session.add(topic)
            topic_objects.append(topic)
        db_session.commit()

    # Create resource
    resource = Resource(
        title="Test Resource",
        description="A test resource with topics",
        content_type="pdf",
        source_url="https://example.com/test",
        storage_path="/test/path.pdf",
        topics=topic_objects
    )
    db_session.add(resource)
    db_session.commit()
    
    return resource


def assert_project_resource_response(data: Dict[str, Any], expected_resource: Resource):
    """Assert that project resource response matches expected data."""
    assert data["id"] == expected_resource.id
    assert data["title"] == expected_resource.title
    assert data["description"] == expected_resource.description
    assert data["content_type"] == expected_resource.content_type


def assert_citation_response(data: Dict[str, Any], expected_citation: Citation):
    """Assert that citation response matches expected data."""
    assert data["resource_id"] == expected_citation.resource_id
    assert data["project_id"] == expected_citation.project_id
    assert data["context"] == expected_citation.context