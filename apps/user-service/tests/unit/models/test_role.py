"""
Comprehensive unit tests for the Role model.
"""
import pytest
from src.models.role import Role, user_roles
from src.models.user import User


class TestRoleModel:
    """Test suite for Role model."""
    
    def test_create_role(self, db_session):
        """Test creating a role with valid data."""
        role = Role(name="editor", description="Editor role")
        db_session.add(role)
        db_session.commit()
        
        assert role.id is not None
        assert role.name == "editor"
        assert role.description == "Editor role"
    
    def test_create_role_without_description(self, db_session):
        """Test creating a role without description."""
        role = Role(name="viewer")
        db_session.add(role)
        db_session.commit()
        
        assert role.id is not None
        assert role.name == "viewer"
        assert role.description is None
    
    def test_role_name_uniqueness(self, db_session):
        """Test that role names must be unique."""
        role1 = Role(name="admin", description="First admin")
        db_session.add(role1)
        db_session.commit()
        
        role2 = Role(name="admin", description="Second admin")
        db_session.add(role2)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
    
    def test_role_repr(self, db_session):
        """Test role string representation."""
        role = Role(name="moderator", description="Moderator role")
        assert repr(role) == "<Role moderator>"
    
    def test_role_users_relationship(self, db_session):
        """Test the many-to-many relationship between roles and users."""
        role = Role(name="admin", description="Admin role")
        db_session.add(role)
        db_session.commit()
        
        user = User(
            email="admin@example.com",
            username="adminuser",
            password="securepass123"
        )
        user.roles.append(role)
        db_session.add(user)
        db_session.commit()
        
        # Verify relationship from role side
        db_session.refresh(role)
        assert len(role.users) == 1
        assert role.users[0].email == "admin@example.com"
        
        # Verify relationship from user side
        assert len(user.roles) >= 1
        assert any(r.name == "admin" for r in user.roles)


class TestRoleFactory:
    """Test suite for RoleFactory."""
    
    def test_role_factory_basic(self, db_session):
        """Test basic role creation with factory."""
        from tests.factories import RoleFactory
        
        RoleFactory._meta.sqlalchemy_session = db_session
        role = RoleFactory()
        
        assert role.id is not None
        assert role.name is not None
        assert role.description is not None
    
    def test_role_factory_with_custom_data(self, db_session):
        """Test role factory with custom data."""
        from tests.factories import RoleFactory
        
        RoleFactory._meta.sqlalchemy_session = db_session
        role = RoleFactory(name="custom_role", description="Custom description")
        
        assert role.name == "custom_role"
        assert role.description == "Custom description"
    
    def test_role_factory_batch_creation(self, db_session):
        """Test creating multiple roles with factory."""
        from tests.factories import create_batch_roles
        
        roles = create_batch_roles(db_session, count=5)
        
        assert len(roles) == 5
        assert all(role.id is not None for role in roles)
        assert len(set(role.name for role in roles)) == 5  # All unique names
    
    def test_role_factory_admin_trait(self, db_session):
        """Test admin role trait."""
        from tests.factories import RoleFactory
        
        RoleFactory._meta.sqlalchemy_session = db_session
        role = RoleFactory(name="admin", description="Administrator role with full permissions")
        
        assert role.name == "admin"
        assert "Administrator" in role.description
    
    def test_role_factory_user_trait(self, db_session):
        """Test user role trait."""
        from tests.factories import RoleFactory
        
        RoleFactory._meta.sqlalchemy_session = db_session
        role = RoleFactory(name="user", description="Default user role")
        
        assert role.name == "user"
        assert "Default" in role.description


class TestUserRolesAssociation:
    """Test suite for user_roles association table."""
    
    def test_user_roles_association(self, db_session):
        """Test the user_roles association table."""
        # Create role
        role = Role(name="editor", description="Editor role")
        db_session.add(role)
        db_session.commit()
        
        # Create user
        user = User(
            email="editor@example.com",
            username="editoruser",
            password="securepass123"
        )
        db_session.add(user)
        db_session.commit()
        
        # Associate user with role
        user.roles.append(role)
        db_session.commit()
        
        # Verify association
        db_session.refresh(user)
        db_session.refresh(role)
        
        assert len(user.roles) >= 1
        assert any(r.name == "editor" for r in user.roles)
        assert len(role.users) == 1
        assert role.users[0].username == "editoruser"
    
    def test_multiple_roles_per_user(self, db_session):
        """Test that a user can have multiple roles."""
        # Create roles
        admin_role = Role(name="admin", description="Admin role")
        editor_role = Role(name="editor", description="Editor role")
        db_session.add_all([admin_role, editor_role])
        db_session.commit()
        
        # Create user with multiple roles
        user = User(
            email="multi@example.com",
            username="multiuser",
            password="securepass123"
        )
        user.roles.extend([admin_role, editor_role])
        db_session.add(user)
        db_session.commit()
        
        # Verify user has multiple roles
        db_session.refresh(user)
        role_names = [r.name for r in user.roles]
        assert "admin" in role_names
        assert "editor" in role_names
    
    def test_multiple_users_per_role(self, db_session):
        """Test that a role can be assigned to multiple users."""
        # Create role
        role = Role(name="viewer", description="Viewer role")
        db_session.add(role)
        db_session.commit()
        
        # Create multiple users with the same role
        user1 = User(
            email="viewer1@example.com",
            username="viewer1",
            password="securepass123"
        )
        user2 = User(
            email="viewer2@example.com",
            username="viewer2",
            password="securepass123"
        )
        
        user1.roles.append(role)
        user2.roles.append(role)
        
        db_session.add_all([user1, user2])
        db_session.commit()
        
        # Verify role has multiple users
        db_session.refresh(role)
        assert len(role.users) == 2
        usernames = [u.username for u in role.users]
        assert "viewer1" in usernames
        assert "viewer2" in usernames
    
    def test_remove_role_from_user(self, db_session):
        """Test removing a role from a user."""
        # Create role and user
        role = Role(name="temp_role", description="Temporary role")
        db_session.add(role)
        db_session.commit()
        
        user = User(
            email="temp@example.com",
            username="tempuser",
            password="securepass123"
        )
        user.roles.append(role)
        db_session.add(user)
        db_session.commit()
        
        # Remove role from user
        user.roles.remove(role)
        db_session.commit()
        
        # Verify role was removed
        db_session.refresh(user)
        assert role not in user.roles
    
    def test_cascade_delete_role(self, db_session):
        """Test that deleting a role doesn't delete associated users."""
        # Create role and user
        role = Role(name="deletable", description="Deletable role")
        db_session.add(role)
        db_session.commit()
        
        user = User(
            email="survivor@example.com",
            username="survivor",
            password="securepass123"
        )
        user.roles.append(role)
        db_session.add(user)
        db_session.commit()
        
        user_id = user.id
        
        # Delete role
        db_session.delete(role)
        db_session.commit()
        
        # Verify user still exists
        surviving_user = db_session.query(User).filter_by(id=user_id).first()
        assert surviving_user is not None
        assert surviving_user.email == "survivor@example.com"
