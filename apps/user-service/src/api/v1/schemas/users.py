"""
Request and response models for user management.
"""
from typing import List
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator


class UserBase(BaseModel):
    """Base model for user data."""
    
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, description="Unique username")
    first_name: str | None = Field(None, description="User's first name")
    last_name: str | None = Field(None, description="User's last name")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
        return v.lower()


class UserCreate(UserBase):
    """Model for user creation."""

    password: str = Field(..., min_length=8, description="User's password")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserUpdate(BaseModel):
    """Model for user updates."""
    
    model_config = ConfigDict(from_attributes=True)

    first_name: str | None = Field(None, description="User's first name")
    last_name: str | None = Field(None, description="User's last name")
    email: EmailStr | None = Field(None, description="User's email address")


class UserResponse(BaseModel):
    """Model for user response."""
    
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    username: str = Field(..., description="User's username")
    first_name: str | None = Field(None, description="User's first name")
    last_name: str | None = Field(None, description="User's last name")
    is_active: bool = Field(..., description="Whether the user is active")
    created_at: datetime = Field(..., description="When the user was created")
    updated_at: datetime = Field(..., description="When the user was last updated")


class UserWithRoles(UserResponse):
    """Model for user response with roles."""

    roles: List[str] = Field(..., description="List of user's role names")


class UserList(BaseModel):
    """Model for list of users response."""
    
    model_config = ConfigDict(from_attributes=True)

    users: List[UserResponse]
    total: int = Field(..., description="Total number of users")


class PasswordChange(BaseModel):
    """Model for password change request."""
    
    model_config = ConfigDict(from_attributes=True)

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v