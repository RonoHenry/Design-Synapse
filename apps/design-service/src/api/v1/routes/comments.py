"""
Comment API routes for the Design Service.

This module provides endpoints for managing comments on designs,
including creating, listing, updating, and deleting comments.

Requirements:
- 7.1: Add comments to designs with timestamp and author
- 7.2: Optional coordinate-based positioning for spatial annotations
- 7.3: Display comments in chronological order
- 7.4: Edit own comments with edited flag
- 7.5: Delete own comments
- 7.6: Project membership required for commenting
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import CurrentUserId, get_current_user_id
from src.api.v1.schemas.requests import CommentCreateRequest, CommentUpdateRequest
from src.api.v1.schemas.responses import DesignCommentResponse
from src.infrastructure.database import get_db
from src.models.design import Design
from src.models.design_comment import DesignComment
from src.services.project_client import ProjectClient, ProjectAccessDeniedError


router = APIRouter(prefix="/api/v1", tags=["comments"])


def get_project_client() -> ProjectClient:
    """Dependency to get ProjectClient instance."""
    return ProjectClient()


async def verify_design_access(
    design_id: int,
    user_id: int,
    db: Session,
    project_client: ProjectClient
) -> Design:
    """
    Verify that a design exists and user has access to it.
    
    Args:
        design_id: ID of the design
        user_id: ID of the current user
        db: Database session
        project_client: Project service client
        
    Returns:
        Design instance if found and accessible
        
    Raises:
        HTTPException: 404 if design not found, 403 if access denied
    """
    # Get design
    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design with ID {design_id} not found"
        )
    
    # Verify project access
    try:
        await project_client.verify_project_access(
            project_id=design.project_id,
            user_id=user_id
        )
    except ProjectAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to project {design.project_id}"
        )
    
    return design


@router.post(
    "/designs/{design_id}/comments",
    response_model=DesignCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a comment on a design",
    description="Add a new comment to a design. Requires project membership. "
                "Supports optional spatial positioning for annotations."
)
async def create_comment(
    design_id: int,
    comment_data: CommentCreateRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    project_client: ProjectClient = Depends(get_project_client)
) -> DesignCommentResponse:
    """
    Create a new comment on a design.
    
    Requirements:
    - 7.1: Store comment with timestamp and author
    - 7.2: Support optional spatial positioning
    - 7.6: Verify project membership
    
    Args:
        design_id: ID of the design to comment on
        comment_data: Comment content and optional position
        user_id: ID of the current user (from JWT token)
        db: Database session
        project_client: Project service client
        
    Returns:
        Created comment with all metadata
        
    Raises:
        HTTPException: 404 if design not found, 403 if access denied,
                      422 if validation fails
    """
    # Verify design exists and user has access
    design = await verify_design_access(design_id, user_id, db, project_client)
    
    # Create comment
    comment = DesignComment(
        design_id=design.id,
        content=comment_data.content,
        created_by=user_id,
        position_x=comment_data.position_x,
        position_y=comment_data.position_y,
        position_z=comment_data.position_z,
    )
    
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    return DesignCommentResponse.model_validate(comment)


@router.get(
    "/designs/{design_id}/comments",
    response_model=List[DesignCommentResponse],
    summary="List comments for a design",
    description="Get all comments for a design in chronological order (oldest first)."
)
async def list_comments(
    design_id: int,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    project_client: ProjectClient = Depends(get_project_client)
) -> List[DesignCommentResponse]:
    """
    List all comments for a design.
    
    Requirements:
    - 7.3: Return comments in chronological order
    - 7.6: Verify project membership
    
    Args:
        design_id: ID of the design
        user_id: ID of the current user (from JWT token)
        db: Database session
        project_client: Project service client
        
    Returns:
        List of comments in chronological order (oldest first)
        
    Raises:
        HTTPException: 404 if design not found, 403 if access denied
    """
    # Verify design exists and user has access
    design = await verify_design_access(design_id, user_id, db, project_client)
    
    # Get comments in chronological order
    comments = (
        db.query(DesignComment)
        .filter(DesignComment.design_id == design.id)
        .order_by(DesignComment.created_at.asc())
        .all()
    )
    
    return [DesignCommentResponse.model_validate(comment) for comment in comments]


@router.put(
    "/comments/{comment_id}",
    response_model=DesignCommentResponse,
    summary="Update a comment",
    description="Update your own comment. Sets the is_edited flag to true."
)
async def update_comment(
    comment_id: int,
    comment_data: CommentUpdateRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    project_client: ProjectClient = Depends(get_project_client)
) -> DesignCommentResponse:
    """
    Update a comment (owner only).
    
    Requirements:
    - 7.4: Allow editing own comments with edited flag
    - 7.6: Verify project membership
    
    Args:
        comment_id: ID of the comment to update
        comment_data: Updated comment content and optional position
        user_id: ID of the current user (from JWT token)
        db: Database session
        project_client: Project service client
        
    Returns:
        Updated comment with is_edited flag set to true
        
    Raises:
        HTTPException: 404 if comment not found, 403 if not owner,
                      422 if validation fails
    """
    # Get comment
    comment = db.query(DesignComment).filter(DesignComment.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with ID {comment_id} not found"
        )
    
    # Verify ownership
    if comment.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own comments"
        )
    
    # Verify project access
    design = await verify_design_access(comment.design_id, user_id, db, project_client)
    
    # Update comment
    comment.content = comment_data.content
    comment.position_x = comment_data.position_x
    comment.position_y = comment_data.position_y
    comment.position_z = comment_data.position_z
    comment.is_edited = True
    comment.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(comment)
    
    return DesignCommentResponse.model_validate(comment)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
    description="Delete your own comment."
)
async def delete_comment(
    comment_id: int,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    project_client: ProjectClient = Depends(get_project_client)
) -> None:
    """
    Delete a comment (owner only).
    
    Requirements:
    - 7.5: Allow deleting own comments
    - 7.6: Verify project membership
    
    Args:
        comment_id: ID of the comment to delete
        user_id: ID of the current user (from JWT token)
        db: Database session
        project_client: Project service client
        
    Raises:
        HTTPException: 404 if comment not found, 403 if not owner
    """
    # Get comment
    comment = db.query(DesignComment).filter(DesignComment.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with ID {comment_id} not found"
        )
    
    # Verify ownership
    if comment.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments"
        )
    
    # Verify project access
    design = await verify_design_access(comment.design_id, user_id, db, project_client)
    
    # Delete comment
    db.delete(comment)
    db.commit()
