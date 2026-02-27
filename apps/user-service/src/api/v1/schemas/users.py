"""
Request and response models for user management.
"""
from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Base model for user data."""

    model_config = ConfigDict(from_attributes=True)

    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=[
            "john.doe@example.com",
            "jane.smith@company.org",
            "admin@designsynapse.com",
        ],
    )
    username: str = Field(
        ...,
        min_length=3,
        description="Unique username",
        examples=["john_doe", "jane-smith", "admin123"],
    )
    first_name: str | None = Field(
        None, description="User's first name", examples=["John", "Jane", "Alice"]
    )
    last_name: str | None = Field(
        None, description="User's last name", examples=["Doe", "Smith", "Johnson"]
    )

    @field_validator("username")
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

    password: str = Field(
        ...,
        min_length=8,
        description="User's password",
        examples=["SecurePass123!", "MyPassword2024", "StrongP@ssw0rd"],
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserUpdate(BaseModel):
    """Model for user updates."""

    model_config = ConfigDict(from_attributes=True)

    first_name: str | None = Field(
        None, description="User's first name", examples=["John", "Jane", "Alice"]
    )
    last_name: str | None = Field(
        None, description="User's last name", examples=["Doe", "Smith", "Johnson"]
    )
    email: EmailStr | None = Field(
        None,
        description="User's email address",
        examples=["john.doe@example.com", "jane.smith@company.org"],
    )


class UserResponse(BaseModel):
    """Model for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="User's unique identifier", examples=[1, 42, 123])
    email: str = Field(
        ...,
        description="User's email address",
        examples=["john.doe@example.com", "jane.smith@company.org"],
    )
    username: str = Field(
        ...,
        description="User's username",
        examples=["john_doe", "jane-smith", "admin123"],
    )
    first_name: str | None = Field(
        None, description="User's first name", examples=["John", "Jane", "Alice"]
    )
    last_name: str | None = Field(
        None, description="User's last name", examples=["Doe", "Smith", "Johnson"]
    )
    is_active: bool = Field(
        ..., description="Whether the user is active", examples=[True, False]
    )
    created_at: datetime = Field(
        ...,
        description="When the user was created",
        examples=["2024-01-15T10:30:00Z", "2024-02-20T14:45:30Z"],
    )
    updated_at: datetime = Field(
        ...,
        description="When the user was last updated",
        examples=["2024-01-15T10:30:00Z", "2024-03-10T09:15:45Z"],
    )


class UserWithRoles(UserResponse):
    """Model for user response with roles."""

    roles: List[str] = Field(
        ...,
        description="List of user's role names",
        examples=[["admin", "user"], ["user"], ["admin", "moderator"]],
    )


class UserList(BaseModel):
    """Model for list of users response."""

    model_config = ConfigDict(from_attributes=True)

    users: List[UserResponse]
    total: int = Field(..., description="Total number of users", examples=[10, 50, 250])


class PasswordChange(BaseModel):
    """Model for password change request."""

    model_config = ConfigDict(from_attributes=True)

    current_password: str = Field(
        ...,
        description="Current password",
        examples=["OldPassword123!", "CurrentPass2024"],
    )
    new_password: str = Field(
        ...,
        min_length=8,
        description="New password",
        examples=["NewSecurePass123!", "UpdatedPassword2024"],
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v
