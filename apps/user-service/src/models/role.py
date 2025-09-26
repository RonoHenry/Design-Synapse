"""Database models for role-based access control."""

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship
from src.infrastructure.database import Base

# Association table for many-to-many relationship between users and roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)


class Role(Base):
    """Role model for role-based access control."""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)

    # Relationship with users through the association table
    users = relationship("User", secondary=user_roles, back_populates="roles")

    def __repr__(self):
        """Get a string representation of the role.

        Returns:
            str: A string in the format "<Role name>"
        """
        return f"<Role {self.name}>"
