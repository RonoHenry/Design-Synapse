"""
Test factories for project service models using factory_boy.

This module provides factory classes for creating test data for Project and Comment models.
"""

import factory
from datetime import datetime, timezone
from typing import Optional

# Import the base factory from common testing package
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from packages.common.testing.base_factory import BaseFactory, TimestampMixin, SequentialNameMixin
from src.models.project import Project
from src.models.comment import Comment


class ProjectFactory(BaseFactory, SequentialNameMixin, TimestampMixin):
    """
    Factory for creating Project model instances.
    
    Usage:
        # Create a project with default values
        project = ProjectFactory.create()
        
        # Create a project with custom values
        project = ProjectFactory.create(name="Custom Project", status="in_progress")
        
        # Build a project without persisting
        project = ProjectFactory.build()
        
        # Create multiple projects
        projects = ProjectFactory.create_batch(5)
    """
    
    class Meta:
        model = Project
        sqlalchemy_session_persistence = "commit"
    
    # Override name from SequentialNameMixin for projects
    name = factory.Sequence(lambda n: f"Test Project {n}")
    description = factory.Faker("text", max_nb_chars=500)
    owner_id = factory.Sequence(lambda n: n + 1)
    status = "draft"
    is_public = False
    is_archived = False
    version = 1
    project_metadata = factory.LazyFunction(dict)
    
    # Timestamps from TimestampMixin
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    
    @factory.post_generation
    def comments(self, create, extracted, **kwargs):
        """
        Handle comments relationship after project creation.
        
        Usage:
            # Create project with 3 comments
            project = ProjectFactory.create(comments=3)
            
            # Create project with specific comments
            project = ProjectFactory.create(comments=[comment1, comment2])
        """
        if not create:
            return
        
        if extracted:
            if isinstance(extracted, int):
                # Create N comments
                CommentFactory.create_batch(extracted, project=self, **kwargs)
            elif isinstance(extracted, list):
                # Add provided comments
                for comment in extracted:
                    comment.project = self
    
    class Params:
        """Traits for common project configurations."""
        
        # Active project trait
        active = factory.Trait(
            status="active",
            is_public=True,
            is_archived=False
        )
        
        # In progress project trait
        in_progress = factory.Trait(
            status="in_progress",
            is_public=False,
            is_archived=False
        )
        
        # Completed project trait
        completed = factory.Trait(
            status="completed",
            is_public=True,
            is_archived=False
        )
        
        # Archived project trait
        archived = factory.Trait(
            status="archived",
            is_public=False,
            is_archived=True
        )
        
        # Public project trait
        public = factory.Trait(
            is_public=True
        )
        
        # Private project trait
        private = factory.Trait(
            is_public=False
        )


class CommentFactory(BaseFactory, TimestampMixin):
    """
    Factory for creating Comment model instances.
    
    Usage:
        # Create a comment (requires project)
        comment = CommentFactory.create(project=project)
        
        # Create a comment with custom content
        comment = CommentFactory.create(content="Custom comment", project=project)
        
        # Create a reply to another comment
        reply = CommentFactory.create(parent=parent_comment, project=project)
        
        # Create multiple comments
        comments = CommentFactory.create_batch(5, project=project)
    """
    
    class Meta:
        model = Comment
        sqlalchemy_session_persistence = "commit"
    
    content = factory.Faker("text", max_nb_chars=1000)
    author_id = factory.Sequence(lambda n: n + 1)
    project_id = None  # Must be provided or use project relationship
    parent_id = None
    
    # Timestamps from TimestampMixin
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    
    # Relationship handling
    project = factory.SubFactory(ProjectFactory)
    parent = None
    
    @factory.lazy_attribute
    def project_id(self):
        """Set project_id from project relationship if not explicitly provided."""
        if self.project:
            return self.project.id
        return None
    
    @factory.lazy_attribute
    def parent_id(self):
        """Set parent_id from parent relationship if not explicitly provided."""
        if self.parent:
            return self.parent.id
        return None
    
    @factory.post_generation
    def replies(self, create, extracted, **kwargs):
        """
        Handle replies relationship after comment creation.
        
        Usage:
            # Create comment with 2 replies
            comment = CommentFactory.create(replies=2, project=project)
            
            # Create comment with specific replies
            comment = CommentFactory.create(replies=[reply1, reply2], project=project)
        """
        if not create:
            return
        
        if extracted:
            if isinstance(extracted, int):
                # Create N replies
                CommentFactory.create_batch(
                    extracted,
                    parent=self,
                    project=self.project,
                    **kwargs
                )
            elif isinstance(extracted, list):
                # Add provided replies
                for reply in extracted:
                    reply.parent = self
                    reply.project = self.project
    
    class Params:
        """Traits for common comment configurations."""
        
        # Top-level comment (no parent)
        top_level = factory.Trait(
            parent_id=None,
            parent=None
        )
        
        # Reply comment (has parent)
        reply = factory.Trait(
            parent=factory.SubFactory('tests.factories.CommentFactory', project=factory.SelfAttribute('..project'))
        )


# Convenience functions for common test scenarios

def create_project_with_comments(session, num_comments: int = 3, **project_kwargs):
    """
    Create a project with a specified number of comments.
    
    Args:
        session: SQLAlchemy session
        num_comments: Number of comments to create
        **project_kwargs: Additional project attributes
        
    Returns:
        Project instance with comments
    """
    ProjectFactory._meta.sqlalchemy_session = session
    CommentFactory._meta.sqlalchemy_session = session
    
    project = ProjectFactory.create(**project_kwargs)
    CommentFactory.create_batch(num_comments, project=project)
    
    return project


def create_comment_thread(session, project, depth: int = 3, **comment_kwargs):
    """
    Create a nested comment thread.
    
    Args:
        session: SQLAlchemy session
        project: Project instance
        depth: Depth of the comment thread
        **comment_kwargs: Additional comment attributes
        
    Returns:
        List of comments in thread order (parent to deepest child)
    """
    CommentFactory._meta.sqlalchemy_session = session
    
    comments = []
    parent = None
    
    for i in range(depth):
        comment = CommentFactory.create(
            project=project,
            parent=parent,
            content=f"Comment at depth {i + 1}",
            **comment_kwargs
        )
        comments.append(comment)
        parent = comment
    
    return comments


def create_project_with_collaborators(session, num_collaborators: int = 3, **project_kwargs):
    """
    Create a project with multiple collaborators (simulated via owner_id variations).
    
    Args:
        session: SQLAlchemy session
        num_collaborators: Number of collaborators
        **project_kwargs: Additional project attributes
        
    Returns:
        Project instance
    """
    ProjectFactory._meta.sqlalchemy_session = session
    
    project = ProjectFactory.create(**project_kwargs)
    
    # Note: Actual collaborator management would be done through the
    # project_collaborators association table, but that requires
    # coordination with the user service
    
    return project
