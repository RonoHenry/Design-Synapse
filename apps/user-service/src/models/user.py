"""
User model definition.
"""
import re
from datetime import datetime, timezone
from typing import List, Optional, Set, cast

from sqlalchemy import Boolean, Column, DateTime, Integer, String, event
from sqlalchemy.orm import Query, relationship
from src.infrastructure.database import Base
from src.models.role import user_roles
from werkzeug.security import check_password_hash, generate_password_hash


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    _password = Column("password", String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_active = Column(Boolean, default=True)

    @property
    def first_name_str(self) -> Optional[str]:
        """Get first name as string."""
        return str(self.first_name) if self.first_name is not None else None

    @property
    def last_name_str(self) -> Optional[str]:
        """Get last name as string."""
        return str(self.last_name) if self.last_name is not None else None

    @property
    def created_at_datetime(self) -> datetime:
        """Get created_at as datetime."""
        return (
            self.created_at
            if isinstance(self.created_at, datetime)
            else datetime.now(timezone.utc)
        )

    @property
    def updated_at_datetime(self) -> datetime:
        """Get updated_at as datetime."""
        return (
            self.updated_at
            if isinstance(self.updated_at, datetime)
            else datetime.now(timezone.utc)
        )

    # Relationship with roles through the association table
    roles = relationship("Role", secondary=user_roles, back_populates="users")

    def __init__(
        self,
        email: str,
        username: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        roles: Optional[List["Role"]] = None,
    ):
        """Initialize a new user."""
        self.email = self._validate_email(email)
        self.username = self._validate_username(username)
        self.password = password  # This will trigger the password.setter
        self.first_name = first_name
        self.last_name = last_name
        self.is_active = True
        self.roles = roles or []

        # Import here to avoid circular imports
        from src.infrastructure.database import SessionLocal
        from src.models.role import Role

        # Add default user role if no roles provided
        if not roles:
            with SessionLocal() as session:
                user_role = session.query(Role).filter_by(name="user").first()
                if not user_role:
                    user_role = Role(name="user", description="Default user role")
                    session.add(user_role)
                    session.commit()
                self.roles = [user_role]

        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at

    @property
    def password(self) -> str:
        """Get password hash."""
        return cast(str, self._password)

    @password.setter
    def password(self, plain_password: str) -> None:
        """Hash and set the password."""
        if not plain_password or len(plain_password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        self._password = generate_password_hash(plain_password)

    def verify_password(self, password: str) -> bool:
        """Check if the provided password matches the hash."""
        return check_password_hash(cast(str, self._password), password)

    @staticmethod
    def _validate_email(email: str) -> str:
        """Validate email format."""
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        if not email_pattern.match(email):
            raise ValueError("Invalid email format")
        return email.lower()

    @staticmethod
    def _validate_username(username: str) -> str:
        """Validate username format."""
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not re.match(r"^[a-zA-Z0-9_-]+$", username):
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
        return username.lower()

    @property
    def role_names(self) -> List[str]:
        """Get list of role names."""
        from src.models.role import Role

        return [cast(str, role.name) for role in cast(List[Role], self.roles)]

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        return any(role.name == role_name for role in self.roles)

    def add_role(self, role: "Role") -> None:  # noqa: F821
        """Add a role to the user."""
        if role not in self.roles:
            self.roles.append(role)

    def remove_role(self, role: "Role") -> None:  # noqa: F821
        """Remove a role from the user."""
        if role in self.roles and role.name != "user":  # Cannot remove base user role
            self.roles.remove(role)
