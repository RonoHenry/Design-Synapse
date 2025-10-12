"""
Factory classes for creating test data in the user service.
"""

import factory
from factory.alchemy import SQLAlchemyModelFactory
from datetime import datetime, timezone
from typing import Optional

# Import the shared testing infrastructure
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'packages'))

from common.testing.base_factory import BaseFactory, FakerMixin, TimestampMixin
from src.models.user import User
from src.models.role import Role


class RoleFactory(BaseFactory):
    """Factory for creating Role instances."""
    
    class Meta:
        model = Role
        sqlalchemy_session_persistence = "commit"
    
    name = factory.Sequence(lambda n: f"role_{n}")
    description = factory.LazyAttribute(lambda obj: f"Description for {obj.name}")
    
    class Params:
        """Traits for different role types."""
        admin = factory.Trait(
            name="admin",
            description="Administrator role with full permissions"
        )
        user = factory.Trait(
            name="user",
            description="Default user role"
        )
        moderator = factory.Trait(
            name="moderator",
            description="Moderator role with limited admin permissions"
        )


class UserFactory(BaseFactory, FakerMixin, TimestampMixin):
    """Factory for creating User instances."""
    
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"
    
    email = factory.Faker("email")
    username = factory.Sequence(lambda n: f"user_{n}")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    
    # Use a simple password for testing
    _password = factory.LazyFunction(
        lambda: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5uDj2"  # "testpass123"
    )
    
    @factory.post_generation
    def roles(self, create, extracted, **kwargs):
        """Handle roles relationship after user creation."""
        if not create:
            return
        
        if extracted:
            # If roles were explicitly provided, use them
            for role in extracted:
                self.roles.append(role)
        else:
            # Create default user role if none provided
            if hasattr(self, '_meta') and hasattr(self._meta, 'sqlalchemy_session'):
                session = self._meta.sqlalchemy_session
                user_role = session.query(Role).filter_by(name="user").first()
                if not user_role:
                    user_role = RoleFactory(name="user", description="Default user role")
                    session.add(user_role)
                    session.commit()
                self.roles.append(user_role)
    
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override create to handle password properly."""
        # Extract password if provided
        password = kwargs.pop('password', 'testpass123')
        
        # Create instance without calling __init__ to avoid role creation issues
        instance = model_class.__new__(model_class)
        
        # Set basic attributes
        for key, value in kwargs.items():
            if key != 'roles':  # Handle roles separately
                setattr(instance, key, value)
        
        # Set password using the property setter for proper hashing
        if not hasattr(instance, '_password') or not instance._password:
            instance.password = password
        
        # Set timestamps if not provided
        if not hasattr(instance, 'created_at') or not instance.created_at:
            instance.created_at = datetime.now(timezone.utc)
        if not hasattr(instance, 'updated_at') or not instance.updated_at:
            instance.updated_at = instance.created_at
        
        # Initialize roles list
        instance.roles = []
        
        return instance
    
    class Params:
        """Traits for different user types."""
        inactive = factory.Trait(
            is_active=False
        )


class UserWithRolesFactory(UserFactory):
    """Factory for creating users with specific roles."""
    
    @factory.post_generation
    def roles(self, create, extracted, **kwargs):
        """Create user with specific roles."""
        if not create:
            return
        
        if extracted:
            for role in extracted:
                self.roles.append(role)
        else:
            # Create both user and admin roles by default
            session = self._meta.sqlalchemy_session if hasattr(self, '_meta') else None
            if session:
                user_role = session.query(Role).filter_by(name="user").first()
                if not user_role:
                    user_role = RoleFactory(name="user")
                    session.add(user_role)
                
                admin_role = session.query(Role).filter_by(name="admin").first()
                if not admin_role:
                    admin_role = RoleFactory(name="admin")
                    session.add(admin_role)
                
                session.commit()
                self.roles.extend([user_role, admin_role])


# Convenience functions for common test scenarios
def create_test_user(session, **kwargs):
    """Create a test user with the given session."""
    UserFactory._meta.sqlalchemy_session = session
    return UserFactory(**kwargs)


def create_test_admin_user(session, **kwargs):
    """Create a test admin user with the given session."""
    UserFactory._meta.sqlalchemy_session = session
    RoleFactory._meta.sqlalchemy_session = session
    
    # Create admin role if it doesn't exist
    admin_role = session.query(Role).filter_by(name="admin").first()
    if not admin_role:
        admin_role = RoleFactory(name="admin", description="Administrator role")
        session.add(admin_role)
        session.commit()
    
    user = UserFactory(**kwargs)
    user.roles.append(admin_role)
    session.add(user)
    session.commit()
    return user


def create_test_role(session, **kwargs):
    """Create a test role with the given session."""
    RoleFactory._meta.sqlalchemy_session = session
    return RoleFactory(**kwargs)


def create_batch_users(session, count=5, **kwargs):
    """Create a batch of test users."""
    UserFactory._meta.sqlalchemy_session = session
    return UserFactory.create_batch(count, **kwargs)


def create_batch_roles(session, count=3, **kwargs):
    """Create a batch of test roles."""
    RoleFactory._meta.sqlalchemy_session = session
    return RoleFactory.create_batch(count, **kwargs)