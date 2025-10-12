"""Additional test cases for Resource and related models."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from knowledge_service.models.resource import Resource, Topic, Citation
from knowledge_service.models.bookmark import Bookmark


@pytest.fixture
def test_topics(db_session: Session):
    """Create test topics."""
    topics = [
        Topic(name=f"Topic {i}", description=f"Description {i}")
        for i in range(3)
    ]
    for topic in topics:
        db_session.add(topic)
    db_session.commit()
    return topics


@pytest.fixture
def test_resource(db_session: Session, test_topics):
    """Create a test resource with topics."""
    resource = Resource(
        title="Test Resource",
        description="Test Description",
        content_type="pdf",
        source_url="https://example.com/test",
        source_platform="Test Platform",
        author="Test Author",
        publication_date=datetime.utcnow(),
        license_type="MIT",
        storage_path="/test/path.pdf",
        file_size=1024,
        topics=test_topics[:2]
    )
    db_session.add(resource)
    db_session.commit()
    return resource


def test_cascade_delete_resource(db_session: Session, test_resource):
    """Test that deleting a resource cascades to related models."""
    # Add bookmark and citation
    bookmark = Bookmark(resource_id=test_resource.id, user_id=1)
    citation = Citation(
        resource_id=test_resource.id,
        project_id=1,
        context="Test citation"
    )
    db_session.add_all([bookmark, citation])
    db_session.commit()

    # Delete resource
    db_session.delete(test_resource)
    db_session.commit()

    # Verify cascade
    assert db_session.query(Bookmark).filter_by(resource_id=test_resource.id).first() is None
    assert db_session.query(Citation).filter_by(resource_id=test_resource.id).first() is None


def test_unique_topic_name(db_session: Session):
    """Test that topic names must be unique."""
    topic1 = Topic(name="Unique Topic", description="First")
    topic2 = Topic(name="Unique Topic", description="Second")
    
    db_session.add(topic1)
    db_session.commit()
    
    with pytest.raises(IntegrityError):
        db_session.add(topic2)
        db_session.commit()


def test_resource_search_by_date_range(db_session: Session):
    """Test searching resources by date range."""
    # Create resources with different dates
    dates = [
        datetime.utcnow() - timedelta(days=i)
        for i in [0, 5, 10, 15]
    ]
    
    for i, date in enumerate(dates):
        resource = Resource(
            title=f"Resource {i}",
            description=f"Description {i}",
            content_type="pdf",
            source_url=f"https://example.com/test{i}",
            publication_date=date,
            storage_path=f"/test/path{i}.pdf"
        )
        db_session.add(resource)
    db_session.commit()

    # Search within last week
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_resources = db_session.query(Resource).filter(
        Resource.publication_date >= week_ago
    ).all()
    assert len(recent_resources) == 2


def test_topic_resource_relationships(db_session: Session, test_topics, test_resource):
    """Test topic-resource many-to-many relationship."""
    # Add another resource with overlapping topics
    new_resource = Resource(
        title="Another Resource",
        description="Another Description",
        content_type="pdf",
        source_url="https://example.com/another",
        storage_path="/test/another.pdf",
        topics=test_topics[1:]  # Overlapping with test_resource
    )
    db_session.add(new_resource)
    db_session.commit()

    # Verify relationships
    shared_topic = test_topics[1]
    assert len(shared_topic.resources) == 2
    assert test_resource in shared_topic.resources
    assert new_resource in shared_topic.resources


def test_resource_validation(db_session: Session):
    """Test resource model validation."""
    # Test invalid URL
    with pytest.raises(ValueError):
        Resource(
            title="Invalid Resource",
            description="Test",
            content_type="pdf",
            source_url="not-a-url",
            storage_path="/test/path.pdf"
        )

    # Test invalid file size
    with pytest.raises(ValueError):
        Resource(
            title="Invalid Resource",
            description="Test",
            content_type="pdf",
            source_url="https://example.com",
            storage_path="/test/path.pdf",
            file_size=-1
        )


def test_bookmark_uniqueness(db_session: Session, test_resource):
    """Test that a user can't bookmark the same resource twice."""
    user_id = 1
    
    # Create first bookmark
    bookmark1 = Bookmark(
        resource_id=test_resource.id,
        user_id=user_id,
        notes="First bookmark"
    )
    db_session.add(bookmark1)
    db_session.commit()

    # Try to create duplicate bookmark
    with pytest.raises(IntegrityError):
        bookmark2 = Bookmark(
            resource_id=test_resource.id,
            user_id=user_id,
            notes="Second bookmark"
        )
        db_session.add(bookmark2)
        db_session.commit()


def test_citation_tracking(db_session: Session, test_resource):
    """Test citation tracking and analytics."""
    # Create multiple citations for the same resource
    project_ids = [1, 2, 3]
    citations = []
    
    for project_id in project_ids:
        citation = Citation(
            resource_id=test_resource.id,
            project_id=project_id,
            context=f"Citation in project {project_id}"
        )
        citations.append(citation)
    
    db_session.add_all(citations)
    db_session.commit()

    # Verify citation count
    citation_count = db_session.query(Citation).filter(
        Citation.resource_id == test_resource.id
    ).count()
    assert citation_count == len(project_ids)

    # Verify unique projects
    unique_projects = db_session.query(Citation.project_id).filter(
        Citation.resource_id == test_resource.id
    ).distinct().count()
    assert unique_projects == len(project_ids)