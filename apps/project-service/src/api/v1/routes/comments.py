"""Comment API routes."""

import sys
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

# Add packages to path for common imports
packages_path = Path(__file__).parent.parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.errors.base import NotFoundError, ForbiddenError

from ..schemas.comment import Comment, CommentCreate, CommentUpdate
from ....core.auth import get_current_user, check_comment_permission
from ....core.exceptions import ProjectNotFoundError
from ....infrastructure.database import get_db
from ....models import Comment as CommentModel, Project as ProjectModel

router = APIRouter(prefix="/projects/{project_id}/comments", tags=["comments"])


@router.post("/", response_model=Comment, status_code=status.HTTP_201_CREATED)
def create_comment(
    project_id: int,
    comment_data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
) -> Comment:
    """Create a new comment on a project."""
    # Check if project exists
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)

    # Validate parent comment if provided
    if comment_data.parent_id:
        parent_comment = (
            db.query(CommentModel)
            .filter(
                CommentModel.id == comment_data.parent_id,
                CommentModel.project_id == project_id
            )
            .first()
        )
        if not parent_comment:
            raise NotFoundError(
                message="Parent comment not found",
                error_code="PARENT_COMMENT_NOT_FOUND",
                details={"parent_id": comment_data.parent_id, "project_id": project_id}
            )

    # Create the comment
    comment = CommentModel(
        **comment_data.model_dump(),
        project_id=project_id,
        author_id=current_user["id"],
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.get("/", response_model=List[Comment])
def list_comments(
    project_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[Comment]:
    """List all comments for a project with pagination."""
    # Check if project exists
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)

    # Get top-level comments (no parent_id)
    comments = (
        db.query(CommentModel)
        .filter(
            CommentModel.project_id == project_id,
            CommentModel.parent_id.is_(None)
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    return comments


@router.get("/{comment_id}", response_model=Comment)
def get_comment(
    project_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
) -> Comment:
    """Get a specific comment by ID."""
    comment = (
        db.query(CommentModel)
        .filter(
            CommentModel.id == comment_id,
            CommentModel.project_id == project_id
        )
        .first()
    )
    if not comment:
        raise NotFoundError(
            message="Comment not found",
            error_code="COMMENT_NOT_FOUND",
            details={"comment_id": comment_id, "project_id": project_id}
        )
    return comment


@router.put("/{comment_id}", response_model=Comment)
def update_comment(
    project_id: int,
    comment_id: int,
    comment_data: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
) -> Comment:
    """Update a comment."""
    # Get both comment and project in one query for efficiency
    comment = (
        db.query(CommentModel, ProjectModel)
        .join(ProjectModel)
        .filter(
            CommentModel.id == comment_id,
            CommentModel.project_id == project_id
        )
        .first()
    )
    if not comment:
        raise NotFoundError(
            message="Comment not found",
            error_code="COMMENT_NOT_FOUND",
            details={"comment_id": comment_id, "project_id": project_id}
        )
    
    comment, project = comment

    # Check if user has permission to update the comment
    if not check_comment_permission(current_user, comment.author_id, project.owner_id):
        raise ForbiddenError(
            message="You don't have permission to update this comment",
            error_code="COMMENT_UPDATE_FORBIDDEN",
            details={"comment_id": comment_id, "user_id": current_user["id"]}
        )

    # Update the comment
    comment.content = comment_data.content
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    project_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
) -> None:
    """Delete a comment."""
    # Get both comment and project in one query for efficiency
    comment = (
        db.query(CommentModel, ProjectModel)
        .join(ProjectModel)
        .filter(
            CommentModel.id == comment_id,
            CommentModel.project_id == project_id
        )
        .first()
    )
    if not comment:
        raise NotFoundError(
            message="Comment not found",
            error_code="COMMENT_NOT_FOUND",
            details={"comment_id": comment_id, "project_id": project_id}
        )
    
    comment, project = comment

    # Check if user has permission to delete the comment
    if not check_comment_permission(current_user, comment.author_id, project.owner_id):
        raise ForbiddenError(
            message="You don't have permission to delete this comment",
            error_code="COMMENT_DELETE_FORBIDDEN",
            details={"comment_id": comment_id, "user_id": current_user["id"]}
        )

    db.delete(comment)
    db.commit()