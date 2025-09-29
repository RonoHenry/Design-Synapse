"""Comment API routes."""

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.v1.schemas.comment import Comment, CommentCreate, CommentUpdate
from src.core.auth import get_current_user, check_comment_permission
from src.infrastructure.database import get_db
from src.models.comment import Comment as CommentModel
from src.models.project import Project as ProjectModel

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found"
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    comment, project = comment

    # Check if user has permission to update the comment
    if not check_comment_permission(current_user, comment.author_id, project.owner_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this comment"
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    comment, project = comment

    # Check if user has permission to delete the comment
    if not check_comment_permission(current_user, comment.author_id, project.owner_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this comment"
        )

    db.delete(comment)
    db.commit()