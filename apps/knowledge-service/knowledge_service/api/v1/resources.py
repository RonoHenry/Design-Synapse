"""API routes for resource management."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import os
import uuid
import logging

from ...models import Resource, Topic, Bookmark
from ...infrastructure.database import get_db
from ..dependencies import get_current_user
from packages.common.auth.models import UserContext
from packages.common.errors.base import ValidationError, NotFoundError, ConflictError
from ...services.pdf_processing import PDFProcessingService
from ...services.batch_processing import BatchProcessingService
from ...services.content_extraction import get_content_extraction_service
from ...core.config import settings
from ...core.error_handling import error_context
from ...core.observability import log_business_event, PerformanceMonitor
from ...exceptions import FileValidationError, PDFProcessingError

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/topics", status_code=status.HTTP_201_CREATED)
@PerformanceMonitor.track_operation("create_topic", "resources_api")
async def create_topic(
    name: str,
    description: Optional[str] = None,
    parent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """Create a new topic."""
    with error_context(
        "create_topic",
        user_id=current_user.user_id,
        topic_name=name
    ):
        # Validate input
        if not name or not name.strip():
            raise ValidationError("Topic name is required")
        
        if len(name) > 100:
            raise ValidationError("Topic name must be 100 characters or less")
        
        # Check for existing topic with same name
        existing_topic = db.query(Topic).filter(Topic.name == name).first()
        if existing_topic:
            raise ConflictError("Topic with this name already exists")
        
        # Validate parent topic if specified
        if parent_id:
            parent_topic = db.query(Topic).filter(Topic.id == parent_id).first()
            if not parent_topic:
                raise NotFoundError("Parent topic", str(parent_id))

        topic = Topic(name=name, description=description, parent_id=parent_id)
        db.add(topic)
        db.commit()
        db.refresh(topic)
        
        # Log business event
        log_business_event(
            "topic_created",
            {
                "topic_id": topic.id,
                "topic_name": name,
                "has_parent": bool(parent_id)
            },
            user_id=current_user.user_id
        )
        
        return topic

@router.get("/topics")
@PerformanceMonitor.track_operation("list_topics", "resources_api")
async def list_topics(
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """List all topics."""
    with error_context(
        "list_topics",
        user_id=current_user.user_id
    ):
        topics = db.query(Topic).all()
        
        # Log business event for analytics
        log_business_event(
            "topics_listed",
            {"topic_count": len(topics)},
            user_id=current_user.user_id
        )
        
        return topics

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


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(...),
    author: Optional[str] = Form(None),
    source_platform: Optional[str] = Form(None),
    topic_ids: Optional[str] = Form(None),  # Comma-separated topic IDs
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    """Upload a file and create a resource with full processing."""
    logger.info(f"Processing file upload: {file.filename}")
    
    # Validate input
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    # Parse topic IDs if provided
    topics = []
    if topic_ids:
        try:
            topic_id_list = [int(tid.strip()) for tid in topic_ids.split(',') if tid.strip()]
            if topic_id_list:
                topics = db.query(Topic).filter(Topic.id.in_(topic_id_list)).all()
                if len(topics) != len(topic_id_list):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="One or more topics not found"
                    )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid topic IDs format"
            )
    
    # Determine content type from file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    content_service = get_content_extraction_service()
    
    if not content_service.is_supported_file_type(file.filename):
        supported_extensions = content_service.get_supported_file_types()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Supported extensions: {', '.join(supported_extensions)}"
        )
    
    if file_extension == '.pdf':
        content_type = 'pdf'
    elif file_extension in ['.docx', '.doc']:
        content_type = 'docx'
    elif file_extension in ['.txt', '.md']:
        content_type = 'text'
    elif file_extension in ['.html', '.htm']:
        content_type = 'html'
    else:
        # Default to text for other supported types
        content_type = 'text'
    
    # Create resource in database first (without storage info)
    source_url = f"upload://{file.filename}"  # Indicate this is an uploaded file
    
    new_resource = Resource(
        title=title,
        description=description,
        content_type=content_type,
        source_url=source_url,
        author=author,
        source_platform=source_platform or "file_upload",
        topics=topics
    )
    db.add(new_resource)
    db.commit()
    db.refresh(new_resource)
    
    try:
        # Process the file based on type
        if content_type == 'pdf':
            pdf_service = PDFProcessingService()
            storage_path, file_size = await pdf_service.process_pdf(file, new_resource, db)
            logger.info(f"Successfully processed PDF for resource {new_resource.id}")
        else:
            # Use content extraction service for other file types
            content_service = get_content_extraction_service()
            storage_path, file_size = await content_service.process_file(file, new_resource, db)
            logger.info(f"Successfully processed {content_type} file for resource {new_resource.id}")
        
        # Refresh resource to get updated data
        db.refresh(new_resource)
        
        # Return resource data with topics
        return {
            "id": new_resource.id,
            "title": new_resource.title,
            "description": new_resource.description,
            "content_type": new_resource.content_type,
            "source_url": new_resource.source_url,
            "source_platform": new_resource.source_platform,
            "author": new_resource.author,
            "storage_path": new_resource.storage_path,
            "file_size": new_resource.file_size,
            "created_at": new_resource.created_at,
            "updated_at": new_resource.updated_at,
            "topics": [{"id": t.id, "name": t.name, "description": t.description} for t in new_resource.topics]
        }
        
    except HTTPException:
        # Clean up resource if processing failed
        db.delete(new_resource)
        db.commit()
        raise
    except Exception as e:
        # Clean up resource if processing failed
        db.delete(new_resource)
        db.commit()
        logger.error(f"Unexpected error processing file upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process uploaded file"
        )


@router.post("/upload/batch", status_code=status.HTTP_201_CREATED)
async def upload_batch_files(
    files: List[UploadFile] = File(...),
    titles: Optional[str] = Form(None),  # Comma-separated titles
    descriptions: Optional[str] = Form(None),  # Comma-separated descriptions
    author: Optional[str] = Form(None),
    source_platform: Optional[str] = Form(None),
    topic_ids: Optional[str] = Form(None),  # Comma-separated topic IDs
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    """Upload multiple files and create resources with concurrent processing."""
    logger.info(f"Processing batch upload of {len(files)} files")
    
    # Parse titles and descriptions if provided
    title_list = None
    description_list = None
    
    if titles:
        title_list = [t.strip() for t in titles.split(',')]
        if len(title_list) != len(files):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of titles must match number of files"
            )
    
    if descriptions:
        description_list = [d.strip() for d in descriptions.split(',')]
        if len(description_list) != len(files):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of descriptions must match number of files"
            )
    
    # Parse topic IDs if provided
    topics = []
    if topic_ids:
        try:
            topic_id_list = [int(tid.strip()) for tid in topic_ids.split(',') if tid.strip()]
            if topic_id_list:
                topics = db.query(Topic).filter(Topic.id.in_(topic_id_list)).all()
                if len(topics) != len(topic_id_list):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="One or more topics not found"
                    )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid topic IDs format"
            )
    
    # Use the batch processing service
    try:
        batch_service = BatchProcessingService()
        batch_result = await batch_service.process_batch(
            files=files,
            titles=title_list,
            descriptions=description_list,
            author=author,
            source_platform=source_platform,
            topics=topics,
            db=db
        )
        
        # Convert batch result to API response format
        return {
            "job_id": batch_result.job_id,
            "status": batch_result.status.value,
            "total_files": batch_result.total_files,
            "successful": batch_result.successful_files,
            "failed": batch_result.failed_files,
            "processing_time_seconds": batch_result.total_processing_time_seconds,
            "results": [
                {
                    "file_index": result.file_index,
                    "filename": result.filename,
                    "success": result.success,
                    "resource": result.resource_data,
                    "error": result.error,
                    "processing_time_seconds": result.processing_time_seconds
                }
                for result in batch_result.results
            ],
            "errors": batch_result.errors
        }
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch processing failed: {str(e)}"
        )


@router.post("/validate", status_code=status.HTTP_200_OK)
async def validate_file(
    file: UploadFile = File(...),
    _: int = Depends(get_current_user)
):
    """Validate a file without processing or storing it."""
    logger.info(f"Validating file: {file.filename}")
    
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    # Check file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    supported_types = settings.file_processing.get_supported_types_list()
    
    validation_result = {
        "filename": file.filename,
        "file_extension": file_extension,
        "is_supported": False,
        "content_type": None,
        "file_size": 0,
        "is_valid_size": False,
        "errors": [],
        "warnings": []
    }
    
    # Use content extraction service to check if file type is supported
    content_service = get_content_extraction_service()
    validation_result["is_supported"] = content_service.is_supported_file_type(file.filename)
    
    # Determine content type
    if file_extension == '.pdf':
        validation_result["content_type"] = 'pdf'
    elif file_extension in ['.docx', '.doc']:
        validation_result["content_type"] = 'docx'
    elif file_extension in ['.txt', '.md']:
        validation_result["content_type"] = 'text'
    elif file_extension in ['.html', '.htm']:
        validation_result["content_type"] = 'html'
    else:
        validation_result["errors"].append(f"Unsupported file type: {file_extension}")
    
    # Check file size
    try:
        content = await file.read()
        validation_result["file_size"] = len(content)
        
        max_size = settings.file_processing.max_file_size_mb * 1024 * 1024
        validation_result["is_valid_size"] = len(content) <= max_size
        
        if not validation_result["is_valid_size"]:
            validation_result["errors"].append(
                f"File too large. Size: {len(content)} bytes, Max: {max_size} bytes"
            )
        
        # Additional validation for PDF files
        if validation_result["content_type"] == 'pdf':
            if not content.startswith(b'%PDF-'):
                validation_result["errors"].append("Invalid PDF file format")
                validation_result["is_supported"] = False
            else:
                # Try to open with PyMuPDF for more detailed validation
                try:
                    import fitz
                    import tempfile
                    
                    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                        temp_file.write(content)
                        temp_file.flush()
                        
                        with fitz.open(temp_file.name) as doc:
                            validation_result["page_count"] = len(doc)
                            validation_result["has_text"] = any(
                                page.get_text().strip() for page in doc
                            )
                            
                            if not validation_result["has_text"]:
                                validation_result["warnings"].append("PDF appears to contain no extractable text")
                    
                    os.unlink(temp_file.name)
                    
                except Exception as e:
                    validation_result["errors"].append(f"PDF validation failed: {str(e)}")
                    validation_result["is_supported"] = False
        
    except Exception as e:
        validation_result["errors"].append(f"Failed to read file content: {str(e)}")
    
    # Overall validation status
    validation_result["is_valid"] = (
        validation_result["is_supported"] and 
        validation_result["is_valid_size"] and 
        len(validation_result["errors"]) == 0
    )
    
    return validation_result


@router.post("/preview", status_code=status.HTTP_200_OK)
async def preview_file_content(
    file: UploadFile = File(...),
    max_length: int = Query(1000, ge=100, le=5000),
    _: int = Depends(get_current_user)
):
    """Preview file content without storing the file."""
    logger.info(f"Previewing content for file: {file.filename}")
    
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    try:
        content_service = get_content_extraction_service()
        preview_data = await content_service.extract_content_preview(file, max_length)
        return preview_data
        
    except Exception as e:
        logger.error(f"Failed to preview file content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview file content: {str(e)}"
        )


@router.get("/upload/config")
async def get_upload_config(
    _: int = Depends(get_current_user)
):
    """Get file upload configuration and limits."""
    content_service = get_content_extraction_service()
    
    return {
        "max_file_size_mb": settings.file_processing.max_file_size_mb,
        "max_batch_size": settings.file_processing.max_batch_size,
        "supported_types": settings.file_processing.get_supported_types_list(),
        "supported_extensions": content_service.get_supported_file_types(),
        "processing_config": {
            "chunk_size": settings.file_processing.chunk_size,
            "chunk_overlap": settings.file_processing.chunk_overlap,
            "enable_auto_tagging": settings.enable_auto_tagging,
            "enable_summary_generation": settings.enable_summary_generation
        }
    }


@router.post("/batch/create", status_code=status.HTTP_201_CREATED)
async def create_batch_job(
    files: List[UploadFile] = File(...),
    titles: Optional[str] = Form(None),  # Comma-separated titles
    descriptions: Optional[str] = Form(None),  # Comma-separated descriptions
    author: Optional[str] = Form(None),
    source_platform: Optional[str] = Form(None),
    topic_ids: Optional[str] = Form(None),  # Comma-separated topic IDs
    priority: Optional[str] = Form("normal"),  # low, normal, high, urgent
    process_immediately: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    """Create a new batch processing job with enhanced options."""
    logger.info(f"Creating batch job with {len(files)} files, priority={priority}")
    
    # Parse priority
    try:
        from ..services.batch_processing import BatchJobPriority
        priority_enum = BatchJobPriority[priority.upper()]
    except (KeyError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid priority. Must be one of: low, normal, high, urgent"
        )
    
    # Parse titles and descriptions if provided
    title_list = None
    description_list = None
    
    if titles:
        title_list = [t.strip() for t in titles.split(',')]
        if len(title_list) != len(files):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of titles must match number of files"
            )
    
    if descriptions:
        description_list = [d.strip() for d in descriptions.split(',')]
        if len(description_list) != len(files):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of descriptions must match number of files"
            )
    
    # Parse topic IDs if provided
    topics = []
    if topic_ids:
        try:
            topic_id_list = [int(tid.strip()) for tid in topic_ids.split(',') if tid.strip()]
            if topic_id_list:
                topics = db.query(Topic).filter(Topic.id.in_(topic_id_list)).all()
                if len(topics) != len(topic_id_list):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="One or more topics not found"
                    )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid topic IDs format"
            )
    
    try:
        batch_service = BatchProcessingService(db_session_factory=lambda: db)
        job_id = await batch_service.create_batch_job(
            files=files,
            titles=title_list,
            descriptions=description_list,
            author=author,
            source_platform=source_platform,
            topics=topics,
            priority=priority_enum,
            user_id=current_user,
            process_immediately=process_immediately,
            db=db
        )
        
        return {
            "job_id": job_id,
            "status": "processing" if process_immediately else "queued",
            "total_files": len(files),
            "priority": priority,
            "process_immediately": process_immediately,
            "message": f"Batch job created with {len(files)} files"
        }
        
    except Exception as e:
        logger.error(f"Failed to create batch job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create batch job: {str(e)}"
        )


@router.get("/batch/jobs/{job_id}/progress")
async def get_job_progress(
    job_id: str,
    _: int = Depends(get_current_user)
):
    """Get real-time progress for a batch processing job."""
    batch_service = BatchProcessingService()
    progress = batch_service.get_job_progress(job_id)
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or no longer active"
        )
    
    return {
        "job_id": progress.job_id,
        "status": progress.status.value,
        "total_files": progress.total_files,
        "processed_files": progress.processed_files,
        "successful_files": progress.successful_files,
        "failed_files": progress.failed_files,
        "current_file": progress.current_file,
        "progress_percentage": progress.progress_percentage,
        "estimated_time_remaining_seconds": progress.estimated_time_remaining_seconds,
        "processing_rate_files_per_second": progress.processing_rate_files_per_second
    }


@router.post("/batch/jobs/{job_id}/cancel")
async def cancel_batch_job(
    job_id: str,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
):
    """Cancel a batch processing job."""
    batch_service = BatchProcessingService()
    success = await batch_service.cancel_job(job_id, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job cannot be cancelled (not found or already completed)"
        )
    
    return {"message": f"Job {job_id} has been cancelled"}


@router.post("/batch/jobs/{job_id}/retry")
async def retry_batch_job(
    job_id: str,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
):
    """Retry a failed batch processing job."""
    batch_service = BatchProcessingService()
    success = await batch_service.retry_job(job_id, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job cannot be retried (not found, not failed, or max retries exceeded)"
        )
    
    return {"message": f"Job {job_id} has been queued for retry"}


@router.post("/batch/jobs/{job_id}/pause")
async def pause_batch_job(
    job_id: str,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
):
    """Pause a running batch processing job."""
    batch_service = BatchProcessingService()
    success = await batch_service.pause_job(job_id, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job cannot be paused (not found or not currently processing)"
        )
    
    return {"message": f"Job {job_id} has been paused"}


@router.post("/batch/jobs/{job_id}/resume")
async def resume_batch_job(
    job_id: str,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
):
    """Resume a paused batch processing job."""
    batch_service = BatchProcessingService()
    success = await batch_service.resume_job(job_id, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job cannot be resumed (not found or not paused)"
        )
    
    return {"message": f"Job {job_id} has been resumed"}


@router.get("/batch/jobs/history")
async def get_batch_job_history(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
):
    """Get batch processing job history."""
    batch_service = BatchProcessingService()
    history = batch_service.get_job_history(limit=limit, db=db)
    
    return {
        "total": len(history),
        "limit": limit,
        "jobs": history
    }


@router.delete("/batch/jobs/cleanup")
async def cleanup_completed_jobs(
    older_than_hours: int = Query(24, ge=1, le=168),  # Max 1 week
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user)
):
    """Clean up completed batch jobs older than specified hours."""
    batch_service = BatchProcessingService()
    batch_service.cleanup_completed_jobs(older_than_hours=older_than_hours, db=db)
    
    return {"message": f"Cleaned up completed jobs older than {older_than_hours} hours"}


@router.get("/batch/stats")
async def get_batch_processing_stats(
    _: int = Depends(get_current_user)
):
    """Get comprehensive batch processing statistics and system status."""
    batch_service = BatchProcessingService()
    return batch_service.get_processing_stats()