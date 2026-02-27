"""
Enhanced resource management API endpoints with content analysis.

This module provides REST API endpoints for enhanced resource processing
including automatic content analysis and tagging.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.common.auth.models import UserContext

from ...core.error_handling import error_context
from ...exceptions import ResourceProcessingError
from ...infrastructure.database import get_db
from ...models.resource import Resource
from ...services.content_analysis import ContentAnalysisService
from ...services.content_extraction import get_content_extraction_service
from ...services.enhanced_resource_processing import (
    EnhancedResourceProcessingService,
    get_enhanced_resource_processing_service)
from ...services.llm import get_llm_service
from ...services.vector_search import get_vector_search_service
from ..dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enhanced-resources", tags=["enhanced-resources"])


def get_enhanced_processing_service(
    content_extraction_service=Depends(get_content_extraction_service),
    vector_search_service=Depends(get_vector_search_service),
    llm_service=Depends(get_llm_service),
) -> EnhancedResourceProcessingService:
    """Get enhanced resource processing service with all dependencies."""
    content_analysis_service = ContentAnalysisService(llm_service)
    return get_enhanced_resource_processing_service(
        content_extraction_service=content_extraction_service,
        content_analysis_service=content_analysis_service,
        vector_search_service=vector_search_service,
        llm_service=llm_service,
    )


@router.post("/process/{resource_id}", response_model=Dict[str, Any])
async def process_resource_with_analysis(
    resource_id: int,
    force_reanalysis: bool = Query(
        False, description="Force re-analysis even if already analyzed"
    ),
    enhanced_service: EnhancedResourceProcessingService = Depends(
        get_enhanced_processing_service
    ),
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Process a resource with comprehensive content analysis."""
    try:
        with error_context(
            "process_resource_api",
            user_id=current_user.user_id,
            resource_id=resource_id,
        ):
            # Get resource
            resource = db.query(Resource).filter(Resource.id == resource_id).first()
            if not resource:
                raise HTTPException(status_code=404, detail="Resource not found")

            # Read file content
            try:
                with open(resource.storage_path, "rb") as f:
                    file_content = f.read()
            except Exception as e:
                logger.error(f"Failed to read file for resource {resource_id}: {e}")
                raise HTTPException(
                    status_code=400, detail="Failed to read resource file"
                )

            # Process resource
            result = await enhanced_service.process_resource_with_analysis(
                resource=resource,
                file_content=file_content,
                db=db,
                force_reanalysis=force_reanalysis,
            )

            return {
                "message": "Resource processed successfully",
                "resource_id": resource_id,
                "processing_results": result,
            }

    except HTTPException:
        raise
    except ResourceProcessingError as e:
        logger.error(f"Resource processing error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Resource processing failed: {e}")
        raise HTTPException(status_code=500, detail="Resource processing failed")


@router.post("/batch-process", response_model=Dict[str, Any])
async def batch_process_resources(
    resource_ids: List[int],
    force_reanalysis: bool = Query(
        False, description="Force re-analysis for all resources"
    ),
    background_tasks: BackgroundTasks = None,
    enhanced_service: EnhancedResourceProcessingService = Depends(
        get_enhanced_processing_service
    ),
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Process multiple resources in batch with content analysis."""
    try:
        with error_context(
            "batch_process_api",
            user_id=current_user.user_id,
            batch_size=len(resource_ids),
        ):
            if not resource_ids:
                raise HTTPException(
                    status_code=400, detail="Resource IDs list cannot be empty"
                )

            if len(resource_ids) > 100:  # Limit batch size
                raise HTTPException(
                    status_code=400, detail="Batch size too large (max 100 resources)"
                )

            # Validate that all resources exist
            existing_resources = (
                db.query(Resource.id).filter(Resource.id.in_(resource_ids)).all()
            )
            existing_ids = {r.id for r in existing_resources}
            missing_ids = set(resource_ids) - existing_ids

            if missing_ids:
                raise HTTPException(
                    status_code=404, detail=f"Resources not found: {list(missing_ids)}"
                )

            if background_tasks and len(resource_ids) > 10:
                # Process large batches in background
                background_tasks.add_task(
                    enhanced_service.batch_process_resources,
                    resource_ids,
                    db,
                    force_reanalysis,
                )
                return {
                    "message": "Batch processing started in background",
                    "resource_count": len(resource_ids),
                    "status": "processing",
                }
            else:
                # Process smaller batches synchronously
                result = await enhanced_service.batch_process_resources(
                    resource_ids=resource_ids, db=db, force_reanalysis=force_reanalysis
                )

                return {
                    "message": "Batch processing completed",
                    "batch_results": result,
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise HTTPException(status_code=500, detail="Batch processing failed")


@router.post("/reanalyze/{resource_id}", response_model=Dict[str, Any])
async def reanalyze_resource(
    resource_id: int,
    enhanced_service: EnhancedResourceProcessingService = Depends(
        get_enhanced_processing_service
    ),
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Re-analyze a specific resource with latest analysis algorithms."""
    try:
        with error_context(
            "reanalyze_resource_api",
            user_id=current_user.user_id,
            resource_id=resource_id,
        ):
            result = await enhanced_service.reanalyze_resource(
                resource_id=resource_id, db=db
            )

            return {
                "message": "Resource re-analysis completed",
                "resource_id": resource_id,
                "analysis_results": result,
            }

    except ResourceProcessingError as e:
        logger.error(f"Resource re-analysis error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Resource re-analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Resource re-analysis failed")


@router.get("/analysis-summary", response_model=Dict[str, Any])
async def get_analysis_summary(
    resource_ids: Optional[List[int]] = Query(
        None, description="Optional list of specific resource IDs"
    ),
    enhanced_service: EnhancedResourceProcessingService = Depends(
        get_enhanced_processing_service
    ),
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get summary of content analysis across resources."""
    try:
        with error_context("analysis_summary_api", user_id=current_user.user_id):
            summary = await enhanced_service.get_analysis_summary(
                resource_ids=resource_ids, db=db
            )

            return {
                "message": "Analysis summary retrieved successfully",
                "summary": summary,
            }

    except Exception as e:
        logger.error(f"Failed to get analysis summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get analysis summary")


@router.get("/{resource_id}/analysis", response_model=Dict[str, Any])
async def get_resource_analysis(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get content analysis results for a specific resource."""
    try:
        with error_context(
            "get_resource_analysis_api",
            user_id=current_user.user_id,
            resource_id=resource_id,
        ):
            # Get resource
            resource = db.query(Resource).filter(Resource.id == resource_id).first()
            if not resource:
                raise HTTPException(status_code=404, detail="Resource not found")

            if not resource.analysis_timestamp:
                return {
                    "message": "Resource has not been analyzed yet",
                    "resource_id": resource_id,
                    "analyzed": False,
                }

            return {
                "message": "Resource analysis retrieved successfully",
                "resource_id": resource_id,
                "analyzed": True,
                "analysis": {
                    "content_classification": resource.content_classification,
                    "complexity_level": resource.complexity_level,
                    "technical_domains": resource.technical_domains,
                    "readability_score": resource.readability_score,
                    "estimated_reading_time": resource.estimated_reading_time,
                    "language": resource.language,
                    "quality_score": resource.quality_score,
                    "auto_tags": resource.auto_tags,
                    "analysis_metadata": resource.analysis_metadata,
                    "analysis_timestamp": resource.analysis_timestamp.isoformat()
                    if resource.analysis_timestamp
                    else None,
                    "keywords": resource.keywords,
                    "summary": resource.summary,
                    "key_takeaways": resource.key_takeaways,
                },
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resource analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to get resource analysis")


@router.get("/search/by-analysis", response_model=Dict[str, Any])
async def search_resources_by_analysis(
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    complexity_level: Optional[str] = Query(
        None, description="Filter by complexity level"
    ),
    technical_domain: Optional[str] = Query(
        None, description="Filter by technical domain"
    ),
    language: Optional[str] = Query(None, description="Filter by language"),
    min_quality_score: Optional[float] = Query(
        None, description="Minimum quality score"
    ),
    max_reading_time: Optional[int] = Query(
        None, description="Maximum reading time in minutes"
    ),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Search resources based on content analysis criteria."""
    try:
        with error_context("search_by_analysis_api", user_id=current_user.user_id):
            # Build query
            query = db.query(Resource).filter(Resource.analysis_timestamp.isnot(None))

            if content_type:
                query = query.filter(Resource.content_classification == content_type)

            if complexity_level:
                query = query.filter(Resource.complexity_level == complexity_level)

            if technical_domain:
                query = query.filter(
                    Resource.technical_domains.contains([technical_domain])
                )

            if language:
                query = query.filter(Resource.language == language)

            if min_quality_score is not None:
                query = query.filter(Resource.quality_score >= min_quality_score)

            if max_reading_time is not None:
                query = query.filter(
                    Resource.estimated_reading_time <= max_reading_time
                )

            if tags:
                for tag in tags:
                    query = query.filter(Resource.auto_tags.contains([tag]))

            # Get total count
            total_count = query.count()

            # Apply pagination
            resources = query.offset(offset).limit(limit).all()

            # Format results
            results = []
            for resource in resources:
                results.append(
                    {
                        "id": resource.id,
                        "title": resource.title,
                        "description": resource.description,
                        "content_classification": resource.content_classification,
                        "complexity_level": resource.complexity_level,
                        "technical_domains": resource.technical_domains,
                        "readability_score": resource.readability_score,
                        "estimated_reading_time": resource.estimated_reading_time,
                        "language": resource.language,
                        "quality_score": resource.quality_score,
                        "auto_tags": resource.auto_tags,
                        "analysis_timestamp": resource.analysis_timestamp.isoformat()
                        if resource.analysis_timestamp
                        else None,
                    }
                )

            return {
                "message": "Search completed successfully",
                "total_count": total_count,
                "returned_count": len(results),
                "offset": offset,
                "limit": limit,
                "resources": results,
            }

    except Exception as e:
        logger.error(f"Search by analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Search by analysis failed")
