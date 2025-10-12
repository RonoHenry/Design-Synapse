"""API routes for resource management."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...models import Resource, Topic, Bookmark
from ...infrastructure.database import get_db
from ..dependencies import get_current_user

router = APIRouter()

@router.post("/topics", status_code=status.HTTP_201_CREATED)
async def create_topic(
    name: str,
    description: Optional[str] = None,
    parent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
):
    """Create a new topic."""
    # Check for existing topic with same name
    if db.query(Topic).filter(Topic.name == name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic with this name already exists"
        )

    topic = Topic(name=name, description=description, parent_id=parent_id)
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic

@router.get("/topics")
async def list_topics(
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
):
    """List all topics."""
    return db.query(Topic).all()

@router.get("/topics/{topic_id}")
async def get_topic(
    topic_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
):
    """Get a specific topic."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    return topic

@router.put("/topics/{topic_id}")
async def update_topic(
    topic_id: int,
    name: str,
    description: Optional[str] = None,
    parent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
):
    """Update a topic."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )

    # Check for existing topic with same name
    existing = db.query(Topic).filter(
        Topic.name == name,
        Topic.id != topic_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic with this name already exists"
        )

    topic.name = name
    topic.description = description
    topic.parent_id = parent_id
    db.commit()
    db.refresh(topic)
    return topic

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_resource(
    resource: dict,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    """Create a new resource."""
    # Validate topics if provided
    topic_ids = resource.get('topic_ids', [])
    if topic_ids:
        topics = db.query(Topic).filter(Topic.id.in_(topic_ids)).all()
        if len(topics) != len(topic_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more topics not found"
            )
    else:
        topics = []

    if not resource.get('title'):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Title is required"
        )
        
    if not resource.get('description'):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Description is required"
        )

    if not resource.get('content_type') or not resource['content_type'] in ['pdf', 'text', 'url', 'image']:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Valid content_type is required"
        )

    if not resource.get('storage_path'):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Storage path is required"
        )

    new_resource = Resource(
        title=resource['title'],
        description=resource.get('description'),
        content_type=resource['content_type'],
        source_url=resource.get('source_url'),
        source_platform=resource.get('source_platform'),
        author=resource.get('author'),
        storage_path=resource['storage_path'],
        file_size=resource.get('file_size'),
        topics=topics
    )
    db.add(new_resource)
    db.commit()
    db.refresh(new_resource)
    
    # Convert the resource to a dict and include topics
    result = {
        "id": new_resource.id,
        "title": new_resource.title,
        "description": new_resource.description,
        "content_type": new_resource.content_type,
        "source_url": new_resource.source_url,
        "source_platform": new_resource.source_platform,
        "author": new_resource.author,
        "publication_date": new_resource.publication_date,
        "doi": new_resource.doi,
        "license_type": new_resource.license_type,
        "summary": new_resource.summary,
        "storage_path": new_resource.storage_path,
        "file_size": new_resource.file_size,
        "created_at": new_resource.created_at,
        "updated_at": new_resource.updated_at,
        "topics": [{"id": t.id, "name": t.name, "description": t.description} for t in new_resource.topics]
    }
    return result

@router.get("/")
async def list_resources(
    content_type: Optional[str] = Query(None, regex="^(pdf|text|url|image)$"),
    topic_id: Optional[int] = None,
    page: int = Query(1, gt=0),
    limit: int = Query(20, gt=0, le=100),
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
):
    """List resources with optional filtering."""
    query = db.query(Resource)
    
    if content_type:
        query = query.filter(Resource.content_type == content_type)
    
    if topic_id:
        query = query.join(Resource.topics).filter(Topic.id == topic_id)

    total = query.count()
    resources = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": resources
    }

@router.post("/bookmarks", status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    data: dict,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    """Create a new bookmark."""
    if 'resource_id' not in data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resource ID is required"
        )
        
    resource = db.query(Resource).filter(Resource.id == data['resource_id']).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    # Check for existing bookmark
    if db.query(Bookmark).filter(
        Bookmark.resource_id == data['resource_id'],
        Bookmark.user_id == current_user
    ).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource already bookmarked"
        )

    bookmark = Bookmark(
        resource_id=data['resource_id'],
        user_id=current_user,
        notes=data.get('notes')
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return bookmark