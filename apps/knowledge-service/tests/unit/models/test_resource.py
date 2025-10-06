"""Comprehensive unit tests for Resource model."""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from knowledge_service.models import Resource, Topic, Citation, Bookmark
from tests.factories import (
    ResourceFactory,
    TopicFactory,
    CitationFactory,
    BookmarkFactory,
    create_resource_with_topics,
    create_resource_with_citations,
)


class TestResourceModel:
    """Test suite for Resource model."""
    
    def test_create_resource_minimal(self, db_session):
        """Test creating a resource with minimal required fields."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory(
            title="Test Resource",
            description="Test description",
            content_type="pdf",
            source_url="https://example.com/resource.pdf",
            storage_path="/storage/resource.pdf"
        )
        
        assert resource.id is not None
        assert resource.title == "Test Resource"
        assert resource.content_type == "pdf"
        assert resource.created_at is not None
        assert resource.updated_at is not None
    
    def test_create_resource_full(self, db_session):
        """Test creating a resource with all fields."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory(
            title="Complete Resource",
            description="Full description",
            content_type="pdf",
            source_url="https://example.com/resource.pdf",
            source_platform="SSRN",
            author="John Doe",
            doi="10.1234/example",
            license_type="MIT",
            summary="Resource summary",
            key_takeaways=["Point 1", "Point 2"],
            keywords=["keyword1", "keyword2"],
            storage_path="/storage/resource.pdf",
            file_size=1024000
        )
        
        assert resource.id is not None
        assert resource.author == "John Doe"
        assert resource.doi == "10.1234/example"
        assert len(resource.key_takeaways) == 2
        assert len(resource.keywords) == 2
    
    def test_resource_url_validation_valid(self, db_session):
        """Test that valid URLs are accepted."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        valid_urls = [
            "https://example.com/resource.pdf",
            "http://localhost:8000/file.pdf",
            "https://subdomain.example.com/path/to/resource",
        ]
        
        for url in valid_urls:
            resource = ResourceFactory(source_url=url)
            assert resource.source_url == url
    
    def test_resource_url_validation_invalid(self, db_session):
        """Test that invalid URLs are rejected."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        with pytest.raises(ValueError, match="Invalid URL format"):
            ResourceFactory(source_url="not-a-valid-url")
    
    def test_resource_file_size_validation(self, db_session):
        """Test file size validation."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        # Valid file size
        resource = ResourceFactory(file_size=1024)
        assert resource.file_size == 1024
        
        # Negative file size should raise error
        with pytest.raises(ValueError, match="File size cannot be negative"):
            ResourceFactory(file_size=-100)
    
    def test_resource_topics_relationship(self, db_session):
        """Test many-to-many relationship with topics."""
        TopicFactory._meta.sqlalchemy_session = db_session
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        topic1 = TopicFactory(name="AI")
        topic2 = TopicFactory(name="Machine Learning")
        
        resource = ResourceFactory()
        resource.topics.extend([topic1, topic2])
        db_session.commit()
        
        db_session.refresh(resource)
        assert len(resource.topics) == 2
        assert topic1 in resource.topics
        assert topic2 in resource.topics
    
    def test_resource_citations_relationship(self, db_session):
        """Test one-to-many relationship with citations."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        CitationFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory()
        
        citation1 = CitationFactory(resource=resource, project_id=1)
        citation2 = CitationFactory(resource=resource, project_id=2)
        
        db_session.refresh(resource)
        assert len(resource.citations) == 2
        assert citation1 in resource.citations
        assert citation2 in resource.citations
    
    def test_resource_bookmarks_relationship(self, db_session):
        """Test one-to-many relationship with bookmarks."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory()
        
        bookmark1 = BookmarkFactory(resource=resource, user_id=1)
        bookmark2 = BookmarkFactory(resource=resource, user_id=2)
        
        db_session.refresh(resource)
        assert len(resource.bookmarks) == 2
        assert bookmark1 in resource.bookmarks
        assert bookmark2 in resource.bookmarks
    
    def test_resource_cascade_delete_citations(self, db_session):
        """Test that deleting a resource cascades to citations."""
        resource = create_resource_with_citations(db_session, citation_count=3)
        resource_id = resource.id
        citation_ids = [c.id for c in resource.citations]
        
        db_session.delete(resource)
        db_session.commit()
        
        # Verify resource is deleted
        assert db_session.query(Resource).filter_by(id=resource_id).first() is None
        
        # Verify citations are also deleted (cascade)
        for citation_id in citation_ids:
            assert db_session.query(Citation).filter_by(id=citation_id).first() is None
    
    def test_resource_cascade_delete_bookmarks(self, db_session):
        """Test that deleting a resource cascades to bookmarks."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory()
        bookmark1 = BookmarkFactory(resource=resource, user_id=1)
        bookmark2 = BookmarkFactory(resource=resource, user_id=2)
        
        resource_id = resource.id
        bookmark_ids = [bookmark1.id, bookmark2.id]
        
        db_session.delete(resource)
        db_session.commit()
        
        # Verify bookmarks are deleted
        for bookmark_id in bookmark_ids:
            assert db_session.query(Bookmark).filter_by(id=bookmark_id).first() is None
    
    def test_resource_repr(self, db_session):
        """Test resource string representation."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory(title="Test Resource")
        assert "Test Resource" in repr(resource)
        assert str(resource.id) in repr(resource)
    
    def test_resource_timestamps(self, db_session):
        """Test that timestamps are set correctly."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory()
        
        assert resource.created_at is not None
        assert resource.updated_at is not None
        assert isinstance(resource.created_at, datetime)
        assert isinstance(resource.updated_at, datetime)
    
    def test_resource_json_fields(self, db_session):
        """Test JSON fields (vector_embedding, key_takeaways, keywords)."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        embedding = {"vector": [0.1, 0.2, 0.3]}
        takeaways = ["Point 1", "Point 2", "Point 3"]
        keywords = ["ai", "ml", "nlp"]
        
        resource = ResourceFactory(
            vector_embedding=embedding,
            key_takeaways=takeaways,
            keywords=keywords
        )
        
        db_session.refresh(resource)
        assert resource.vector_embedding == embedding
        assert resource.key_takeaways == takeaways
        assert resource.keywords == keywords


class TestTopicModel:
    """Test suite for Topic model."""
    
    def test_create_topic(self, db_session):
        """Test creating a topic."""
        TopicFactory._meta.sqlalchemy_session = db_session
        
        topic = TopicFactory(name="Artificial Intelligence", description="AI topics")
        
        assert topic.id is not None
        assert topic.name == "Artificial Intelligence"
        assert topic.description == "AI topics"
    
    def test_topic_name_uniqueness(self, db_session):
        """Test that topic names must be unique."""
        TopicFactory._meta.sqlalchemy_session = db_session
        
        TopicFactory(name="Unique Topic")
        
        with pytest.raises(IntegrityError):
            TopicFactory(name="Unique Topic")
            db_session.commit()
    
    def test_topic_hierarchical_relationship(self, db_session):
        """Test parent-child relationship between topics."""
        TopicFactory._meta.sqlalchemy_session = db_session
        
        parent = TopicFactory(name="Computer Science")
        child1 = TopicFactory(name="AI", parent_id=parent.id)
        child2 = TopicFactory(name="Databases", parent_id=parent.id)
        
        db_session.refresh(parent)
        assert len(parent.children) == 2
        assert child1 in parent.children
        assert child2 in parent.children
    
    def test_topic_resources_relationship(self, db_session):
        """Test many-to-many relationship with resources."""
        TopicFactory._meta.sqlalchemy_session = db_session
        ResourceFactory._meta.sqlalchemy_session = db_session
        
        topic = TopicFactory(name="Machine Learning")
        resource1 = ResourceFactory()
        resource2 = ResourceFactory()
        
        topic.resources.extend([resource1, resource2])
        db_session.commit()
        
        db_session.refresh(topic)
        assert len(topic.resources) == 2
        assert resource1 in topic.resources
        assert resource2 in topic.resources
    
    def test_topic_repr(self, db_session):
        """Test topic string representation."""
        TopicFactory._meta.sqlalchemy_session = db_session
        
        topic = TopicFactory(name="Test Topic")
        assert "Test Topic" in repr(topic)


class TestCitationModel:
    """Test suite for Citation model."""
    
    def test_create_citation(self, db_session):
        """Test creating a citation."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        CitationFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory()
        citation = CitationFactory(
            resource=resource,
            project_id=1,
            context="Used in introduction",
            created_by=1
        )
        
        assert citation.id is not None
        assert citation.resource_id == resource.id
        assert citation.project_id == 1
        assert citation.context == "Used in introduction"
    
    def test_citation_resource_relationship(self, db_session):
        """Test relationship with resource."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        CitationFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory()
        citation = CitationFactory(resource=resource)
        
        assert citation.resource == resource
        assert citation in resource.citations
    
    def test_citation_cascade_delete(self, db_session):
        """Test that citation is deleted when resource is deleted."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        CitationFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory()
        citation = CitationFactory(resource=resource)
        citation_id = citation.id
        
        db_session.delete(resource)
        db_session.commit()
        
        assert db_session.query(Citation).filter_by(id=citation_id).first() is None
    
    def test_citation_repr(self, db_session):
        """Test citation string representation."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        CitationFactory._meta.sqlalchemy_session = db_session
        
        citation = CitationFactory(project_id=42)
        assert "42" in repr(citation)


class TestBookmarkModel:
    """Test suite for Bookmark model."""
    
    def test_create_bookmark(self, db_session):
        """Test creating a bookmark."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory()
        bookmark = BookmarkFactory(
            user_id=1,
            resource=resource,
            notes="Important resource"
        )
        
        assert bookmark.id is not None
        assert bookmark.user_id == 1
        assert bookmark.resource_id == resource.id
        assert bookmark.notes == "Important resource"
    
    def test_bookmark_unique_constraint(self, db_session):
        """Test that user can only bookmark a resource once."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory()
        BookmarkFactory(user_id=1, resource=resource)
        
        with pytest.raises(IntegrityError):
            BookmarkFactory(user_id=1, resource=resource)
            db_session.commit()
    
    def test_bookmark_user_id_positive_constraint(self, db_session):
        """Test that user_id must be positive."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory()
        
        with pytest.raises(IntegrityError):
            BookmarkFactory(user_id=0, resource=resource)
            db_session.commit()
    
    def test_bookmark_cascade_delete(self, db_session):
        """Test that bookmark is deleted when resource is deleted."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session
        
        resource = ResourceFactory()
        bookmark = BookmarkFactory(resource=resource, user_id=1)
        bookmark_id = bookmark.id
        
        db_session.delete(resource)
        db_session.commit()
        
        assert db_session.query(Bookmark).filter_by(id=bookmark_id).first() is None
    
    def test_bookmark_repr(self, db_session):
        """Test bookmark string representation."""
        ResourceFactory._meta.sqlalchemy_session = db_session
        BookmarkFactory._meta.sqlalchemy_session = db_session
        
        bookmark = BookmarkFactory(user_id=5)
        assert "5" in repr(bookmark)
