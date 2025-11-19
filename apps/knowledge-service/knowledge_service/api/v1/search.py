"""API routes for searching knowledge resources."""

from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime
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
    AUTHOR = "author"
    FILE_SIZE = "file_size"

class SortOrder(str, Enum):
    """Enum for sort order."""
    ASC = "asc"
    DESC = "desc"

router = APIRouter()

@router.get("/global")
async def search_global(
    query: str = Query(..., description="Search query"),
    resource_type: ResourceType = Query(ResourceType.ALL, description="Filter by resource type"),
    min_score: float = Query(0.0, description="Minimum relevance score (0-1)", ge=0.0, le=1.0),
    sort_by: SortBy = Query(SortBy.RELEVANCE, description="Sort results by"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order (asc/desc)"),
    tags: List[str] = Query(None, description="Filter by tags"),
    # Advanced filters
    author: Optional[str] = Query(None, description="Filter by author name"),
    source_platform: Optional[str] = Query(None, description="Filter by source platform"),
    license_type: Optional[str] = Query(None, description="Filter by license type"),
    date_from: Optional[datetime] = Query(None, description="Filter by publication date from (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter by publication date to (ISO format)"),
    min_file_size: Optional[int] = Query(None, description="Minimum file size in bytes", ge=0),
    max_file_size: Optional[int] = Query(None, description="Maximum file size in bytes", ge=0),
    has_doi: Optional[bool] = Query(None, description="Filter resources with/without DOI"),
    keywords: List[str] = Query(None, description="Filter by keywords"),
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
        sort_order=sort_order,
        tags=tags,
        author=author,
        source_platform=source_platform,
        license_type=license_type,
        date_from=date_from,
        date_to=date_to,
        min_file_size=min_file_size,
        max_file_size=max_file_size,
        has_doi=has_doi,
        keywords=keywords,
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
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order (asc/desc)"),
    tags: List[str] = Query(None, description="Filter by tags"),
    # Advanced filters
    author: Optional[str] = Query(None, description="Filter by author name"),
    source_platform: Optional[str] = Query(None, description="Filter by source platform"),
    license_type: Optional[str] = Query(None, description="Filter by license type"),
    date_from: Optional[datetime] = Query(None, description="Filter by publication date from (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter by publication date to (ISO format)"),
    min_file_size: Optional[int] = Query(None, description="Minimum file size in bytes", ge=0),
    max_file_size: Optional[int] = Query(None, description="Maximum file size in bytes", ge=0),
    has_doi: Optional[bool] = Query(None, description="Filter resources with/without DOI"),
    keywords: List[str] = Query(None, description="Filter by keywords"),
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
        sort_order=sort_order,
        tags=tags,
        author=author,
        source_platform=source_platform,
        license_type=license_type,
        date_from=date_from,
        date_to=date_to,
        min_file_size=min_file_size,
        max_file_size=max_file_size,
        has_doi=has_doi,
        keywords=keywords,
        page=page,
        page_size=page_size
    )

@router.get("/project/{project_id}/recommendations")
async def get_project_recommendations(
    project_id: int,
    resource_type: ResourceType = Query(ResourceType.ALL, description="Filter by resource type"),
    min_score: float = Query(0.3, description="Minimum relevance score (0-1)", ge=0.0, le=1.0),
    sort_by: SortBy = Query(SortBy.RELEVANCE, description="Sort results by"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order (asc/desc)"),
    tags: List[str] = Query(None, description="Filter by tags"),
    # Advanced filters
    author: Optional[str] = Query(None, description="Filter by author name"),
    source_platform: Optional[str] = Query(None, description="Filter by source platform"),
    license_type: Optional[str] = Query(None, description="Filter by license type"),
    date_from: Optional[datetime] = Query(None, description="Filter by publication date from (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter by publication date to (ISO format)"),
    min_file_size: Optional[int] = Query(None, description="Minimum file size in bytes", ge=0),
    max_file_size: Optional[int] = Query(None, description="Maximum file size in bytes", ge=0),
    has_doi: Optional[bool] = Query(None, description="Filter resources with/without DOI"),
    keywords: List[str] = Query(None, description="Filter by keywords"),
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
        sort_by=sort_by,
        sort_order=sort_order,
        tags=tags,
        author=author,
        source_platform=source_platform,
        license_type=license_type,
        date_from=date_from,
        date_to=date_to,
        min_file_size=min_file_size,
        max_file_size=max_file_size,
        has_doi=has_doi,
        keywords=keywords,
        page=page,
        page_size=page_size
    )