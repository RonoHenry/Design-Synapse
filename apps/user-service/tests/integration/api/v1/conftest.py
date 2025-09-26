"""Fixtures for profile API tests."""

import pytest
from sqlalchemy.orm import Session

from src.models.role import Role


@pytest.fixture(scope="session")
def default_roles(db_engine):
    """Create default roles for testing."""
    session = Session(db_engine)
    try:
        # Check if roles already exist
        user_role = session.query(Role).filter_by(name="user").first()
        admin_role = session.query(Role).filter_by(name="admin").first()

        if not user_role:
            user_role = Role(name="user", description="Regular user")
            session.add(user_role)

        if not admin_role:
            admin_role = Role(name="admin", description="Administrator")
            session.add(admin_role)

        session.commit()
        return user_role, admin_role
    finally:
        session.close()


@pytest.fixture
def user_role(default_roles):
    """Return the user role for testing."""
    return default_roles[0]
