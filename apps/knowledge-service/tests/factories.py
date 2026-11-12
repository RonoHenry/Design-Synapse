"""Test factories for knowledge service models using factory_boy."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import factory
from factory import Faker, LazyAttribute, SubFactory, post_generation
from factory.alchemy import SQLAlchemyModelFactory

# Add packages to path for shared testing utilities
packages_path = Path(__file__).parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.testing.base_factory import BaseFactory

from knowledge_service.models import Resource, Topic, Citation, Bookmark


class TopicFactory(BaseFactory):
    """Factory for creating Topic instances."""
    
    class Meta:
        model = Topic
        sqlalchemy_session_persistence = "commit"
    
    name = Faker("word")
    description = Faker("sentence", nb_words=10)
    parent_id = None
    
    @post_generation
    def resources(self, create, extracted, **kwargs):
        """Handle many-to-many relationship with resources."""
        if not create:
            return
        
        if extracted:
            for resource in extracted:
                self.resources.append(resource)


class ResourceFactory(BaseFactory):
    """Factory for creating Resource instances."""
    
    class Meta:
        model = Resource
        sqlalchemy_session_persistence = "commit"
    
    title = Faker("sentence", nb_words=6)
    description = Faker("text", max_nb_chars=200)
    content_type = "pdf"
    source_url = Faker("url")
    source_platform = Faker("random_element", elements=["SSRN", "MDPI", "arXiv", "IEEE"])
    vector_embedding = None
    
    # Additional metadata
    author = Faker("name")
    publication_date = LazyAttribute(
        lambda _: datetime.utcnow() - timedelta(days=factory.Faker("random_int", min=1, max=365).generate())
    )
    doi = LazyAttribute(lambda _: f"10.{factory.Faker('random_int', min=1000, max=9999).generate()}/{factory.Faker('random_int', min=100000, max=999999).generate()}")
    license_type = Faker("random_element", elements=["MIT", "Apache-2.0", "GPL-3.0", "CC-BY-4.0"])
    
    # Generated content
    summary = Faker("text", max_nb_chars=500)
    key_takeaways = LazyAttribute(lambda _: [factory.Faker("sentence").generate() for _ in range(3)])
    keywords = LazyAttribute(lambda _: [factory.Faker("word").generate() for _ in range(5)])
    
    # Storage info
    storage_path = Faker("file_path", depth=3, extension="pdf")
    file_size = Faker("random_int", min=1024, max=10485760)  # 1KB to 10MB
    
    # Timestamps
    created_at = LazyAttribute(lambda _: datetime.utcnow())
    updated_at = LazyAttribute(lambda _: datetime.utcnow())
    
    @post_generation
    def topics(self, create, extracted, **kwargs):
        """Handle many-to-many relationship with topics."""
        if not create:
            return
        
        if extracted:
            for topic in extracted:
                self.topics.append(topic)


class CitationFactory(BaseFactory):
    """Factory for creating Citation instances."""
    
    class Meta:
        model = Citation
        sqlalchemy_session_persistence = "commit"
    
    resource = SubFactory(ResourceFactory)
    resource_id = LazyAttribute(lambda obj: obj.resource.id if obj.resource else None)
    project_id = Faker("random_int", min=1, max=1000)
    context = Faker("text", max_nb_chars=300)
    created_at = LazyAttribute(lambda _: datetime.utcnow())
    created_by = Faker("random_int", min=1, max=100)


class BookmarkFactory(BaseFactory):
    """Factory for creating Bookmark instances."""
    
    class Meta:
        model = Bookmark
        sqlalchemy_session_persistence = "commit"
    
    user_id = Faker("random_int", min=1, max=100)
    resource = SubFactory(ResourceFactory)
    resource_id = LazyAttribute(lambda obj: obj.resource.id if obj.resource else None)
    notes = Faker("text", max_nb_chars=200)
    created_at = LazyAttribute(lambda _: datetime.utcnow())


# Helper functions for creating test data

def create_resource_with_topics(session, topic_count: int = 2, **kwargs) -> Resource:
    """Create a resource with associated topics.
    
    Args:
        session: Database session
        topic_count: Number of topics to create
        **kwargs: Additional resource attributes
        
    Returns:
        Resource instance with topics
    """
    TopicFactory._meta.sqlalchemy_session = session
    ResourceFactory._meta.sqlalchemy_session = session
    
    topics = [TopicFactory() for _ in range(topic_count)]
    resource = ResourceFactory(topics=topics, **kwargs)
    
    return resource


def create_resource_with_citations(session, citation_count: int = 3, **kwargs) -> Resource:
    """Create a resource with citations.
    
    Args:
        session: Database session
        citation_count: Number of citations to create
        **kwargs: Additional resource attributes
        
    Returns:
        Resource instance with citations
    """
    ResourceFactory._meta.sqlalchemy_session = session
    CitationFactory._meta.sqlalchemy_session = session
    
    resource = ResourceFactory(**kwargs)
    
    for _ in range(citation_count):
        CitationFactory(resource=resource)
    
    session.refresh(resource)
    return resource


def create_resource_with_bookmarks(session, bookmark_count: int = 2, **kwargs) -> Resource:
    """Create a resource with bookmarks.
    
    Args:
        session: Database session
        bookmark_count: Number of bookmarks to create
        **kwargs: Additional resource attributes
        
    Returns:
        Resource instance with bookmarks
    """
    ResourceFactory._meta.sqlalchemy_session = session
    BookmarkFactory._meta.sqlalchemy_session = session
    
    resource = ResourceFactory(**kwargs)
    
    for i in range(bookmark_count):
        BookmarkFactory(resource=resource, user_id=i + 1)
    
    session.refresh(resource)
    return resource


def create_batch_resources(session, count: int = 5, **kwargs) -> List[Resource]:
    """Create multiple resources.
    
    Args:
        session: Database session
        count: Number of resources to create
        **kwargs: Additional resource attributes
        
    Returns:
        List of Resource instances
    """
    ResourceFactory._meta.sqlalchemy_session = session
    return [ResourceFactory(**kwargs) for _ in range(count)]


def create_batch_topics(session, count: int = 5, **kwargs) -> List[Topic]:
    """Create multiple topics.
    
    Args:
        session: Database session
        count: Number of topics to create
        **kwargs: Additional topic attributes
        
    Returns:
        List of Topic instances
    """
    TopicFactory._meta.sqlalchemy_session = session
    return [TopicFactory(**kwargs) for _ in range(count)]


def create_hierarchical_topics(session, parent_count: int = 2, children_per_parent: int = 3) -> List[Topic]:
    """Create hierarchical topic structure.
    
    Args:
        session: Database session
        parent_count: Number of parent topics
        children_per_parent: Number of children per parent
        
    Returns:
        List of all created topics (parents and children)
    """
    TopicFactory._meta.sqlalchemy_session = session
    
    all_topics = []
    
    for _ in range(parent_count):
        parent = TopicFactory()
        all_topics.append(parent)
        
        for _ in range(children_per_parent):
            child = TopicFactory(parent_id=parent.id)
            all_topics.append(child)
    
    return all_topics
