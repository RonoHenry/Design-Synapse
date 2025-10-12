"""API routes for managing citations."""

from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.infrastructure.database import get_db
from src.models.resource import Citation
from src.services.project_knowledge import ProjectKnowledgeService
from src.api.dependencies import get_current_user

router = APIRouter(
    prefix="/citations",
    tags=["citations"]
)

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_citation(
    *,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
    resource_id: int,
    project_id: int,
    context: str,
) -> Dict:
    """Create a new citation."""
    service = ProjectKnowledgeService()
    try:
        citation = await service.add_citation(
            db=db,
            resource_id=resource_id,
            project_id=project_id,
            context=context,
            user_id=user_id
        )
        return {
            "id": citation.id,
            "resource_id": citation.resource_id,
            "project_id": citation.project_id,
            "context": citation.context,
            "created_by": citation.created_by,
            "created_at": citation.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/project/{project_id}/analytics")
async def get_project_citations(
    project_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
) -> Dict:
    """Get citation analytics for a project."""
    service = ProjectKnowledgeService()
    return service.get_citation_analytics(db, project_id)