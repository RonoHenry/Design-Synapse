"""
Request and response models for role management.
"""
from typing import List

from pydantic import BaseModel, Field, ConfigDict


class RoleBase(BaseModel):
    """Base model for role data."""
    
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="The unique name of the role")
    description: str | None = Field(
        None, description="A description of the role's purpose"
    )


class RoleCreate(RoleBase):
    """Model for creating a new role."""

    pass


class RoleResponse(RoleBase):
    """Model for role responses."""

    id: int = Field(..., description="The unique identifier of the role")


class RoleList(BaseModel):
    """Model for list of roles response."""
    
    model_config = ConfigDict(from_attributes=True)

    roles: List[RoleResponse]
    total: int = Field(..., description="Total number of roles")


class RoleAssignmentResponse(BaseModel):
    """Model for role assignment response."""
    
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(..., description="Success message")
    user_id: int = Field(..., description="The ID of the user")
    role_name: str = Field(..., description="The name of the role")


class UserRolesResponse(BaseModel):
    """Model for user roles response."""
    
    model_config = ConfigDict(from_attributes=True)

    roles: List[RoleResponse]
