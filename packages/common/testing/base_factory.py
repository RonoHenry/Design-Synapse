"""
Base factory classes for consistent test data creation across services.
"""

import factory
from factory.alchemy import SQLAlchemyModelFactory
from typing import Type, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone


class BaseFactory(SQLAlchemyModelFactory):
    """
    Base factory class that provides common patterns for all model factories.
    
    This class establishes consistent patterns for:
    - Session management
    - Common field patterns (timestamps, IDs)
    - Sequence generation
    - Trait definitions
    """
    
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "commit"
    
    # Common timestamp fields
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    
    @classmethod
    def _setup_next_sequence(cls):
        """Override to ensure sequences start from a predictable value."""
        return 1
    
    @classmethod
    def create_batch_with_session(cls, session: Session, size: int, **kwargs) -> list:
        """
        Create a batch of instances with a specific session.
        
        Args:
            session: SQLAlchemy session to use
            size: Number of instances to create
            **kwargs: Additional factory parameters
            
        Returns:
            List of created instances
        """
        original_session = cls._meta.sqlalchemy_session
        cls._meta.sqlalchemy_session = session
        try:
            return cls.create_batch(size, **kwargs)
        finally:
            cls._meta.sqlalchemy_session = original_session
    
    @classmethod
    def build_batch_with_session(cls, session: Session, size: int, **kwargs) -> list:
        """
        Build a batch of instances without persisting them.
        
        Args:
            session: SQLAlchemy session to use
            size: Number of instances to build
            **kwargs: Additional factory parameters
            
        Returns:
            List of built instances (not persisted)
        """
        original_session = cls._meta.sqlalchemy_session
        cls._meta.sqlalchemy_session = session
        try:
            return cls.build_batch(size, **kwargs)
        finally:
            cls._meta.sqlalchemy_session = original_session


class TimestampMixin:
    """Mixin for factories that need timestamp fields."""
    
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class UserReferenceMixin:
    """Mixin for factories that reference user IDs."""
    
    # Default user ID for testing - services should override this
    # with their own user creation logic
    user_id = factory.Sequence(lambda n: n)
    created_by = factory.Sequence(lambda n: n)
    owner_id = factory.Sequence(lambda n: n)


class SequentialNameMixin:
    """Mixin for factories that need sequential names."""
    
    name = factory.Sequence(lambda n: f"Test Item {n}")
    title = factory.Sequence(lambda n: f"Test Title {n}")


class FakerMixin:
    """Mixin providing common Faker patterns."""
    
    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    description = factory.Faker("text", max_nb_chars=500)
    content = factory.Faker("text", max_nb_chars=1000)
    url = factory.Faker("url")
    
    @factory.lazy_attribute
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


def create_factory_for_model(
    model_class: Type,
    session: Session,
    base_factory: Type[BaseFactory] = BaseFactory,
    **field_overrides
) -> Type[BaseFactory]:
    """
    Dynamically create a factory for a given model class.
    
    Args:
        model_class: SQLAlchemy model class
        session: Database session
        base_factory: Base factory class to inherit from
        **field_overrides: Field definitions to override
        
    Returns:
        Factory class for the model
    """
    
    class Meta:
        model = model_class
        sqlalchemy_session = session
    
    factory_attrs = {
        "Meta": Meta,
        **field_overrides
    }
    
    factory_name = f"{model_class.__name__}Factory"
    return type(factory_name, (base_factory,), factory_attrs)
