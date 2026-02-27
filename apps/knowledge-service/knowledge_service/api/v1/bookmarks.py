"""API routes for bookmark management."""
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ...infrastructure.database import get_db
from ...models import Bookmark, Resource
from ..dependencies import get_current_user
from .schemas import BookmarkCreate

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    data: dict,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
):
    """Create a new bookmark."""
    if "resource_id" not in data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resource ID is required",
        )

    resource = db.query(Resource).filter(Resource.id == data["resource_id"]).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
        )

    # Check for existing bookmark
    existing_bookmark = (
        db.query(Bookmark)
        .filter(
            Bookmark.resource_id == data["resource_id"],
            Bookmark.user_id == current_user,
        )
        .first()
    )

    if existing_bookmark:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource already bookmarked",
        )

    bookmark = Bookmark(
        resource_id=data["resource_id"], user_id=current_user, notes=data.get("notes")
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return bookmark


@router.get("/")
async def list_bookmarks(
    page: int = Query(1, gt=0),
    limit: int = Query(20, gt=0, le=100),
    resource_id: Optional[int] = Query(None, description="Filter by resource ID"),
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
):
    """List user's bookmarks with pagination and optional filtering."""
    query = db.query(Bookmark).filter(Bookmark.user_id == current_user)

    # Apply resource filter if provided
    if resource_id:
        query = query.filter(Bookmark.resource_id == resource_id)

    # Order by creation date (newest first)
    query = query.order_by(Bookmark.created_at.desc())

    total = query.count()
    bookmarks = query.offset((page - 1) * limit).limit(limit).all()

    return {"total": total, "page": page, "limit": limit, "items": bookmarks}


@router.get("/{bookmark_id}")
async def get_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
):
    """Get a specific bookmark."""
    bookmark = (
        db.query(Bookmark)
        .filter(Bookmark.id == bookmark_id, Bookmark.user_id == current_user)
        .first()
    )

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found"
        )

    return bookmark


@router.put("/{bookmark_id}")
async def update_bookmark(
    bookmark_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
):
    """Update a bookmark's notes."""
    bookmark = (
        db.query(Bookmark)
        .filter(Bookmark.id == bookmark_id, Bookmark.user_id == current_user)
        .first()
    )

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found"
        )

    # Update notes if provided
    if "notes" in data:
        bookmark.notes = data["notes"]

    db.commit()
    db.refresh(bookmark)
    return bookmark


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
):
    """Delete a bookmark."""
    bookmark = (
        db.query(Bookmark)
        .filter(Bookmark.id == bookmark_id, Bookmark.user_id == current_user)
        .first()
    )

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found"
        )

    db.delete(bookmark)
    db.commit()
    return None


@router.get("/resource/{resource_id}")
async def get_bookmark_by_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
):
    """Get user's bookmark for a specific resource."""
    bookmark = (
        db.query(Bookmark)
        .filter(Bookmark.resource_id == resource_id, Bookmark.user_id == current_user)
        .first()
    )

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found for this resource",
        )

    return bookmark


@router.post("/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_bookmarks(
    bookmark_ids: dict,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
):
    """Delete multiple bookmarks at once."""
    if "bookmark_ids" not in bookmark_ids or not bookmark_ids["bookmark_ids"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bookmark IDs are required",
        )

    ids = bookmark_ids["bookmark_ids"]
    if not isinstance(ids, list) or not all(isinstance(id, int) for id in ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bookmark IDs must be a list of integers",
        )

    # Find bookmarks that belong to the current user
    bookmarks = (
        db.query(Bookmark)
        .filter(Bookmark.id.in_(ids), Bookmark.user_id == current_user)
        .all()
    )

    if len(bookmarks) != len(ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more bookmarks not found or don't belong to user",
        )

    # Delete all bookmarks
    for bookmark in bookmarks:
        db.delete(bookmark)

    db.commit()
    return None
