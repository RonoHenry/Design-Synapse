"""API routes for citations."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...models import Resource, Citation
from ...infrastructure.database import get_db
from ..dependencies import get_current_user
from .schemas import CitationCreate

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_citation(
    data: CitationCreate,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    """Create a new citation."""
    # Check if resource exists
    resource = db.query(Resource).filter(Resource.id == data.resource_id).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    # Create citation
    citation = Citation(
        resource_id=data.resource_id,
        project_id=data.project_id,
        created_by=current_user,
        context=data.context
    )
    db.add(citation)
    db.commit()
    db.refresh(citation)
    return citation

@router.get("/project/{project_id}")
async def list_project_citations(
    project_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
):
    """List all citations for a project."""
    citations = (
        db.query(Citation)
        .filter(Citation.project_id == project_id)
        .order_by(Citation.created_at.desc())
        .all()
    )
    return citations

@router.get("/resource/{resource_id}")
async def list_resource_citations(
    resource_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
):
    """List all citations of a resource."""
    citations = (
        db.query(Citation)
        .filter(Citation.resource_id == resource_id)
        .order_by(Citation.created_at.desc())
        .all()
    )
    return citations