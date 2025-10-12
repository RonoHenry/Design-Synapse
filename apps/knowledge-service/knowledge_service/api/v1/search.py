"""API routes for searching knowledge resources."""

from enum import Enum
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...infrastructure.database import get_db
from ...services.project_knowledge import ProjectKnowledgeService
from ..dependencies import get_current_user

class ResourceType(str, Enum):
    """Enum for resource types."""
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    URL = "url"
    ALL = "all"

class SortBy(str, Enum):
    """Enum for sorting options."""
    RELEVANCE = "relevance"
    DATE = "date"
    TITLE = "title"
    TYPE = "type"

router = APIRouter()

@router.get("/global")
async def search_global(
    query: str = Query(..., description="Search query"),
    resource_type: ResourceType = Query(ResourceType.ALL, description="Filter by resource type"),
    min_score: float = Query(0.0, description="Minimum relevance score (0-1)", ge=0.0, le=1.0),
    sort_by: SortBy = Query(SortBy.RELEVANCE, description="Sort results by"),
    tags: List[str] = Query(None, description="Filter by tags"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(20, description="Results per page", ge=1, le=100),
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
) -> Dict:
    """Search across all knowledge resources globally."""
    service = ProjectKnowledgeService()
    return await service.search_global(
        db=db,
        query=query,
        resource_type=resource_type,
        min_score=min_score,
        sort_by=sort_by,
        tags=tags,
        page=page,
        page_size=page_size
    )

@router.get("/project/{project_id}")
async def search_project_knowledge(
    project_id: int,
    query: str = Query(..., description="Search query"),
    include_global: bool = Query(True, description="Include resources not yet cited in project"),
    resource_type: ResourceType = Query(ResourceType.ALL, description="Filter by resource type"),
    min_score: float = Query(0.0, description="Minimum relevance score (0-1)", ge=0.0, le=1.0),
    sort_by: SortBy = Query(SortBy.RELEVANCE, description="Sort results by"),
    tags: List[str] = Query(None, description="Filter by tags"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(20, description="Results per page", ge=1, le=100),
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
) -> Dict:
    """Search for knowledge resources in project context."""
    service = ProjectKnowledgeService()
    return await service.search_project_knowledge(
        db=db,
        project_id=project_id,
        query=query,
        include_global=include_global,
        resource_type=resource_type,
        min_score=min_score,
        sort_by=sort_by,
        tags=tags,
        page=page,
        page_size=page_size
    )

@router.get("/project/{project_id}/recommendations")
async def get_project_recommendations(
    project_id: int,
    resource_type: ResourceType = Query(ResourceType.ALL, description="Filter by resource type"),
    min_score: float = Query(0.3, description="Minimum relevance score (0-1)", ge=0.0, le=1.0),
    tags: List[str] = Query(None, description="Filter by tags"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(20, description="Results per page", ge=1, le=100),
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
) -> Dict:
    """Get recommended resources for a project with filtering and pagination."""
    service = ProjectKnowledgeService()
    return await service.get_recommendations(
        db=db,
        project_id=project_id,
        resource_type=resource_type,
        min_score=min_score,
        tags=tags,
        page=page,
        page_size=page_size
    )