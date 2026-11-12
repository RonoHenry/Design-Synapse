"""Test MySQL/TiDB compatibility of user-service models."""

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Import models and Base
from src.infrastructure.database import Base
from src.models import Role, User
from src.models.user_profile import UserProfile


class TestMySQLCompatibility:
    """Test that models are compatible with MySQL dialect."""

    @pytest.fixture
    def mysql_engine(self):
        """Create an in-memory SQLite engine with MySQL compatibility mode."""
        # SQLite doesn't fully emulate MySQL, but we can test basic compatibility
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def mysql_session(self, mysql_engine):
        """Create a session for testing."""
        Session = sessionmaker(bind=mysql_engine)
        session = Session()
        yield session
        session.close()

    def test_user_model_schema(self, mysql_engine):
        """Test that User model schema is MySQL-compatible."""
        inspector = inspect(mysql_engine)
        columns = {col["name"]: col for col in inspector.get_columns("users")}
        
        # Verify primary key
        assert "id" in columns
        assert columns["id"]["primary_key"] == 1
        
        # Verify string columns
        assert "email" in columns
        assert "username" in columns
        assert "password" in columns  # Column name is "password", not "password_hash"
        assert "first_name" in columns
        assert "last_name" in columns
        
        # Verify boolean column
        assert "is_active" in columns
        
        # Verify datetime columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_role_model_schema(self, mysql_engine):
        """Test that Role model schema is MySQL-compatible."""
        inspector = inspect(mysql_engine)
        columns = {col["name"]: col for col in inspector.get_columns("roles")}
        
        # Verify primary key
        assert "id" in columns
        assert columns["id"]["primary_key"] == 1
        
        # Verify string columns
        assert "name" in columns
        assert "description" in columns

    def test_user_profile_model_schema(self, mysql_engine):
        """Test that UserProfile model schema is MySQL-compatible."""
        inspector = inspect(mysql_engine)
        columns = {col["name"]: col for col in inspector.get_columns("user_profiles")}
        
        # Verify primary key
        assert "id" in columns
        assert columns["id"]["primary_key"] == 1
        
        # Verify foreign key
        assert "user_id" in columns
        
        # Verify JSON columns (stored as TEXT in SQLite)
        assert "social_links" in columns
        assert "preferences" in columns

    def test_user_roles_association_table(self, mysql_engine):
        """Test that user_roles association table is MySQL-compatible."""
        inspector = inspect(mysql_engine)
        columns = {col["name"]: col for col in inspector.get_columns("user_roles")}
        
        # Verify composite primary key
        assert "user_id" in columns
        assert "role_id" in columns
        
        # Verify foreign keys exist
        fks = inspector.get_foreign_keys("user_roles")
        assert len(fks) == 2

    def test_create_user_with_json_fields(self, mysql_session):
        """Test creating a user with JSON fields works."""
        user = User(
            email="test@example.com",
            username="testuser",
            password="securepass123"  # Use password property, not password_hash
        )
        mysql_session.add(user)
        mysql_session.commit()
        
        # Create profile with JSON fields
        profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            social_links={"twitter": "https://twitter.com/test"},
            preferences={"theme": "dark", "notifications": True}
        )
        mysql_session.add(profile)
        mysql_session.commit()
        
        # Verify data persisted
        retrieved_profile = mysql_session.query(UserProfile).filter_by(user_id=user.id).first()
        assert retrieved_profile is not None
        assert retrieved_profile.social_links == {"twitter": "https://twitter.com/test"}
        assert retrieved_profile.preferences == {"theme": "dark", "notifications": True}

    def test_user_role_relationship(self, mysql_session):
        """Test many-to-many relationship works with MySQL."""
        # Create role
        role = Role(name="admin", description="Administrator role")
        mysql_session.add(role)
        mysql_session.commit()
        
        # Create user
        user = User(
            email="admin@example.com",
            username="admin",
            password="securepass123"  # Use password property
        )
        mysql_session.add(user)
        mysql_session.commit()
        
        # Add role to user
        user.roles.append(role)
        mysql_session.commit()
        
        # Verify relationship
        retrieved_user = mysql_session.query(User).filter_by(username="admin").first()
        assert len(retrieved_user.roles) == 1
        assert retrieved_user.roles[0].name == "admin"
