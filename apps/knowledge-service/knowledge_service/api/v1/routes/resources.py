"""API routes for knowledge resource management."""

from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session

from src.api.v1.schemas.resource import (
    Bookmark, BookmarkCreate, BookmarkUpdate,
    Citation, CitationCreate,
    Resource, ResourceCreate, ResourceUpdate,
    Topic, TopicCreate, TopicUpdate
)
from src.core.auth import get_current_user
from src.core.vector_search import get_vector_search_service
from src.infrastructure.database import get_db
from src.models.resource import Resource as ResourceModel
from src.models.resource import Topic as TopicModel
from src.models.resource import Bookmark as BookmarkModel
from src.models.resource import Citation as CitationModel
from src.services.vector_search import VectorSearchService

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.post("/topics", response_model=Topic)
async def create_topic(
    topic: TopicCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
) -> TopicModel:
    """Create a new topic."""
    # Check if topic with same name exists
    existing = db.query(TopicModel).filter(
        TopicModel.name == topic.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic with this name already exists"
        )
    
    # Create topic
    db_topic = TopicModel(**topic.model_dump())
    db.add(db_topic)
    db.commit()
    db.refresh(db_topic)
    return db_topic


@router.get("/topics", response_model=List[Topic])
async def list_topics(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
) -> List[TopicModel]:
    """List all topics."""
    return db.query(TopicModel).offset(skip).limit(limit).all()


@router.get("/topics/{topic_id}", response_model=Topic)
async def get_topic(
    topic_id: int,
    db: Session = Depends(get_db)
) -> TopicModel:
    """Get a specific topic."""
    topic = db.query(TopicModel).filter(TopicModel.id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    return topic


@router.put("/topics/{topic_id}", response_model=Topic)
async def update_topic(
    topic_id: int,
    topic_update: TopicUpdate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
) -> TopicModel:
    """Update a topic."""
    topic = db.query(TopicModel).filter(TopicModel.id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    
    # Update topic
    for key, value in topic_update.model_dump(exclude_unset=True).items():
        setattr(topic, key, value)
    
    db.commit()
    db.refresh(topic)
    return topic


@router.post("/resources", response_model=Resource)
async def create_resource(
    resource: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
    vector_search: VectorSearchService = Depends(get_vector_search_service)
) -> ResourceModel:
    """Create a new resource."""
    # Verify topics exist
    topics = db.query(TopicModel).filter(
        TopicModel.id.in_(resource.topic_ids)
    ).all()
    if len(topics) != len(resource.topic_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more topics not found"
        )
    
    # Create resource
    db_resource = ResourceModel(
        **resource.model_dump(exclude={"topic_ids"}),
        topics=topics
    )
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    
    # Index in vector search
    await vector_search.index_resource(
        db_resource.id,
        db_resource.title,
        db_resource.description,
        "",  # Content will be added when file is processed
        {
            "content_type": db_resource.content_type,
            "source_platform": db_resource.source_platform,
            "author": db_resource.author,
            "topics": [topic.name for topic in topics]
        }
    )
    
    return db_resource


@router.get("/resources", response_model=List[Resource])
async def list_resources(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    topic_id: Optional[int] = None,
    search_query: Optional[str] = None,
    db: Session = Depends(get_db),
    vector_search: VectorSearchService = Depends(get_vector_search_service)
) -> List[ResourceModel]:
    """List resources with optional filtering and search."""
    query = db.query(ResourceModel)
    
    # Filter by topic if specified
    if topic_id:
        query = query.filter(ResourceModel.topics.any(id=topic_id))
    
    # If search query provided, use vector search
    if search_query:
        search_results = await vector_search.search_resources(
            search_query,
            filter_metadata={"topic_id": topic_id} if topic_id else None
        )
        resource_ids = [result["resource_id"] for result in search_results]
        query = query.filter(ResourceModel.id.in_(resource_ids))
    
    return query.offset(skip).limit(limit).all()


@router.post("/bookmarks", response_model=Bookmark)
async def create_bookmark(
    bookmark: BookmarkCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
) -> BookmarkModel:
    """Create a new bookmark."""
    # Check if resource exists
    resource = db.query(ResourceModel).filter(
        ResourceModel.id == bookmark.resource_id
    ).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    # Check if bookmark already exists
    existing = db.query(BookmarkModel).filter(
        BookmarkModel.user_id == current_user["id"],
        BookmarkModel.resource_id == bookmark.resource_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource already bookmarked"
        )
    
    # Create bookmark
    db_bookmark = BookmarkModel(
        **bookmark.model_dump(),
        user_id=current_user["id"]
    )
    db.add(db_bookmark)
    db.commit()
    db.refresh(db_bookmark)
    return db_bookmark


@router.post("/citations", response_model=Citation)
async def create_citation(
    citation: CitationCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
) -> CitationModel:
    """Create a new citation."""
    # Check if resource exists
    resource = db.query(ResourceModel).filter(
        ResourceModel.id == citation.resource_id
    ).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    # Create citation
    db_citation = CitationModel(
        **citation.model_dump(),
        created_by=current_user["id"]
    )
    db.add(db_citation)
    db.commit()
    db.refresh(db_citation)
    return db_citation


@router.get("/search", response_model=List[Resource])
async def search_resources(
    query: str,
    topic_id: Optional[int] = None,
    content_type: Optional[str] = None,
    source_platform: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    vector_search: VectorSearchService = Depends(get_vector_search_service)
) -> List[ResourceModel]:
    """Search resources using semantic search."""
    # Build metadata filter
    filter_metadata = {}
    if topic_id:
        filter_metadata["topic_id"] = topic_id
    if content_type:
        filter_metadata["content_type"] = content_type
    if source_platform:
        filter_metadata["source_platform"] = source_platform
    
    # Perform vector search
    search_results = await vector_search.search_resources(
        query,
        filter_metadata=filter_metadata if filter_metadata else None,
        top_k=limit
    )
    
    # Get resources from database
    resource_ids = [result["resource_id"] for result in search_results]
    resources = db.query(ResourceModel).filter(
        ResourceModel.id.in_(resource_ids)
    ).all()
    
    # Sort resources to match search order
    id_to_resource = {resource.id: resource for resource in resources}
    return [id_to_resource[id] for id in resource_ids if id in id_to_resource]