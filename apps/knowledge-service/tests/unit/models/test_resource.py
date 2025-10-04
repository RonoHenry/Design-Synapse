"""Unit tests for knowledge resource models."""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from knowledge_service.models.resource import Resource, Topic, Citation
from knowledge_service.models.bookmark import Bookmark


def test_create_topic(db_session):
    """Test creating a new topic."""
    topic = Topic(
        name="Sustainable Design",
        description="Principles and practices of sustainable architecture"
    )
    db_session.add(topic)
    db_session.commit()

    assert topic.id is not None
    assert topic.name == "Sustainable Design"
    assert topic.description == "Principles and practices of sustainable architecture"
    assert topic.parent_id is None


def test_create_topic_with_parent(db_session):
    """Test creating a topic with a parent topic."""
    parent = Topic(
        name="Architecture",
        description="General architecture topics"
    )
    db_session.add(parent)
    db_session.commit()

    child = Topic(
        name="Modern Architecture",
        description="Contemporary architectural styles",
        parent_id=parent.id
    )
    db_session.add(child)
    db_session.commit()

    assert child.parent_id == parent.id
    db_session.refresh(parent)
    assert len(parent.children) == 1
    assert parent.children[0].name == "Modern Architecture"


def test_create_duplicate_topic(db_session):
    """Test that duplicate topic names are not allowed."""
    topic1 = Topic(
        name="Construction",
        description="Construction methods"
    )
    db_session.add(topic1)
    db_session.commit()

    topic2 = Topic(
        name="Construction",
        description="Different description"
    )
    db_session.add(topic2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_create_resource(db_session):
    """Test creating a new resource."""
    topic = Topic(
        name="BIM",
        description="Building Information Modeling"
    )
    db_session.add(topic)
    db_session.commit()

    resource = Resource(
        title="BIM Best Practices",
        description="Guide to BIM implementation",
        content_type="pdf",
        source_url="https://example.com/bim-guide",
        source_platform="MDPI",
        author="John Doe",
        publication_date=datetime.utcnow(),
        license_type="CC BY-SA",
        storage_path="/path/to/file.pdf",
        file_size=1024,
        topics=[topic]
    )
    db_session.add(resource)
    db_session.commit()

    assert resource.id is not None
    assert resource.title == "BIM Best Practices"
    assert len(resource.topics) == 1
    assert resource.topics[0].name == "BIM"
    assert resource.created_at is not None
    assert resource.updated_at is not None


def test_resource_required_fields(db_session):
    """Test that required fields are enforced."""
    resource = Resource(
        title="Incomplete Resource"
        # Missing required fields
    )
    db_session.add(resource)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_create_bookmark(db_session):
    """Test creating a bookmark."""
    topic = Topic(name="Testing", description="Test topic")
    db_session.add(topic)
    db_session.commit()

    resource = Resource(
        title="Test Resource",
        description="Test description",
        content_type="pdf",
        source_url="https://example.com/test",
        source_platform="Test Platform",
        license_type="MIT",
        storage_path="/test/path.pdf",
        file_size=100,
        topics=[topic]
    )
    db_session.add(resource)
    db_session.commit()

    bookmark = Bookmark(
        user_id=1,
        resource_id=resource.id,
        notes="Important resource"
    )
    db_session.add(bookmark)
    db_session.commit()

    assert bookmark.id is not None
    assert bookmark.user_id == 1
    assert bookmark.resource.title == "Test Resource"
    assert bookmark.notes == "Important resource"


def test_create_citation(db_session):
    """Test creating a citation."""
    topic = Topic(name="Testing", description="Test topic")
    db_session.add(topic)
    db_session.commit()

    resource = Resource(
        title="Test Resource",
        description="Test description",
        content_type="pdf",
        source_url="https://example.com/test",
        source_platform="Test Platform",
        license_type="MIT",
        storage_path="/test/path.pdf",
        file_size=100,
        topics=[topic]
    )
    db_session.add(resource)
    db_session.commit()

    citation = Citation(
        resource_id=resource.id,
        project_id=1,
        context="Used in project calculations",
        created_by=1
    )
    db_session.add(citation)
    db_session.commit()

    assert citation.id is not None
    assert citation.resource.title == "Test Resource"
    assert citation.context == "Used in project calculations"


def test_cascade_delete_resource(db_session):
    """Test that deleting a resource cascades to bookmarks and citations."""
    topic = Topic(name="Testing", description="Test topic")
    db_session.add(topic)
    db_session.commit()

    resource = Resource(
        title="Test Resource",
        description="Test description",
        content_type="pdf",
        source_url="https://example.com/test",
        source_platform="Test Platform",
        license_type="MIT",
        storage_path="/test/path.pdf",
        file_size=100,
        topics=[topic]
    )
    db_session.add(resource)
    db_session.commit()

    bookmark = Bookmark(user_id=1, resource_id=resource.id)
    citation = Citation(
        resource_id=resource.id,
        project_id=1,
        context="Test citation",
        created_by=1
    )
    db_session.add(bookmark)
    db_session.add(citation)
    db_session.commit()

    # Delete resource
    db_session.delete(resource)
    db_session.commit()

    # Check that bookmark and citation were deleted
    assert db_session.query(Bookmark).count() == 0
    assert db_session.query(Citation).count() == 0