"""
API endpoints for role management.
"""
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from src.api.dependencies import get_current_user, has_role
from src.api.v1.schemas.roles import (
    RoleAssignmentResponse,
    RoleCreate,
    RoleList,
    RoleResponse,
    UserRolesResponse,
)
from src.core.exceptions import NotFoundError, ValidationError
from src.infrastructure.database import get_db
from src.models.role import Role
from src.models.user import User

router = APIRouter()


@router.get("/roles", response_model=RoleList)
def list_roles(
    db: Session = Depends(get_db), _: bool = Depends(has_role(["admin"]))
) -> RoleList:
    """
    List all available roles.

    Requires admin role.
    Returns a paginated list of roles.
    """
    roles = db.query(Role).all()
    return RoleList(roles=roles, total=len(roles))


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(has_role(["admin"])),
) -> Role:
    """
    Create a new role.

    Requires admin role.
    Returns the created role.
    """
    # Check if role with same name exists
    existing_role = db.query(Role).filter(Role.name == role_data.name).first()
    if existing_role:
        raise ValidationError(
            message="Role with this name already exists",
            details={"name": role_data.name},
        )

    role = Role(**role_data.dict())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.post(
    "/users/{user_id}/roles/{role_name}", response_model=RoleAssignmentResponse
)
def assign_role_to_user(
    user_id: int,
    role_name: str,
    db: Session = Depends(get_db),
    _: bool = Depends(has_role(["admin"])),
) -> RoleAssignmentResponse:
    """
    Assign a role to a user.

    Requires admin role.
    Returns a success message with the assignment details.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User", str(user_id))

    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise NotFoundError("Role", role_name)

    user.add_role(role)
    db.commit()
    return RoleAssignmentResponse(
        message=f"Role {role_name} assigned to user {user.email}",
        user_id=user_id,
        role_name=role_name,
    )


@router.delete(
    "/users/{user_id}/roles/{role_name}", response_model=RoleAssignmentResponse
)
def remove_role_from_user(
    user_id: int,
    role_name: str,
    db: Session = Depends(get_db),
    _: bool = Depends(has_role(["admin"])),
) -> RoleAssignmentResponse:
    """
    Remove a role from a user.

    Requires admin role.
    Cannot remove the 'user' role.
    Returns a success message with the removal details.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User", str(user_id))

    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise NotFoundError("Role", role_name)

    if role.name == "user":
        raise ValidationError("Cannot remove the base user role")

    user.remove_role(role)
    db.commit()
    return RoleAssignmentResponse(
        message=f"Role {role_name} removed from user {user.email}",
        user_id=user_id,
        role_name=role_name,
    )


@router.get("/users/me/roles", response_model=List[RoleResponse])
def get_my_roles(current_user: User = Depends(get_current_user)) -> List[RoleResponse]:
    """
    Get the roles of the current authenticated user.

    Returns a list of roles assigned to the current user.
    """
    return current_user.roles
