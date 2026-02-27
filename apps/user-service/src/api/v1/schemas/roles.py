"""Request and response models for role management operations."""

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class RoleBase(BaseModel):
    """Base model for role data."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(
        ...,
        description="The unique name of the role",
        examples=["admin", "user", "moderator", "editor"],
    )
    description: str | None = Field(
        None,
        description="A description of the role's purpose",
        examples=[
            "Administrator with full system access",
            "Regular user with basic permissions",
            "Content moderator",
        ],
    )


class RoleCreate(RoleBase):
    """Model for creating a new role."""

    pass


class RoleResponse(RoleBase):
    """Model for role responses."""

    id: int = Field(
        ..., description="The unique identifier of the role", examples=[1, 2, 3]
    )


class RoleList(BaseModel):
    """Model for list of roles response."""

    model_config = ConfigDict(from_attributes=True)

    roles: List[RoleResponse]
    total: int = Field(..., description="Total number of roles", examples=[3, 5, 10])


class RoleAssignmentResponse(BaseModel):
    """Model for role assignment response."""

    model_config = ConfigDict(from_attributes=True)

    message: str = Field(
        ...,
        description="Success message",
        examples=["Role assigned successfully", "Role removed successfully"],
    )
    user_id: int = Field(..., description="The ID of the user", examples=[1, 42, 123])
    role_name: str = Field(
        ..., description="The name of the role", examples=["admin", "user", "moderator"]
    )


class UserRolesResponse(BaseModel):
    """Model for user roles response."""

    model_config = ConfigDict(from_attributes=True)

    roles: List[RoleResponse]
