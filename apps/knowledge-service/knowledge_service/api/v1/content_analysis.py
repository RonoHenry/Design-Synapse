"""
Content analysis and tagging API endpoints.

This module provides REST API endpoints for content analysis,
automatic tagging, and content classification.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from packages.common.auth.models import UserContext

from ...core.error_handling import error_context
from ...exceptions import ContentProcessingError
from ...interfaces.services import IContentExtractionService, ILLMService
from ...services.content_analysis import (ContentAnalysis,
                                          ContentAnalysisService)
from ...services.content_extraction import get_content_extraction_service
from ...services.llm import get_llm_service
from ..dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content-analysis", tags=["content-analysis"])


def get_content_analysis_service(
    llm_service: ILLMService = Depends(get_llm_service),
) -> ContentAnalysisService:
    """Get content analysis service instance."""
    return ContentAnalysisService(llm_service)


@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_content(
    content: str = Form(...),
    title: Optional[str] = Form(None),
    metadata: Optional[Dict[str, Any]] = Form(None),
    content_analysis_service: ContentAnalysisService = Depends(
        get_content_analysis_service
    ),
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Analyze text content and return comprehensive analysis results."""
    try:
        with error_context("analyze_content_api", user_id=current_user.user_id):
            if not content or not content.strip():
                raise HTTPException(status_code=400, detail="Content cannot be empty")

            if len(content) > 1000000:  # 1MB limit
                raise HTTPException(
                    status_code=400, detail="Content too large (max 1MB)"
                )

            analysis = await content_analysis_service.analyze_content(
                content=content, title=title or "", metadata=metadata or {}
            )

            return {
                "content_type": analysis.content_type.value,
                "complexity_level": analysis.complexity_level.value,
                "technical_domains": analysis.technical_domains,
                "key_concepts": analysis.key_concepts,
                "readability_score": analysis.readability_score,
                "estimated_reading_time": analysis.estimated_reading_time,
                "language": analysis.language,
                "quality_score": analysis.quality_score,
                "tags": analysis.tags,
                "metadata": analysis.metadata,
            }

    except ContentProcessingError as e:
        logger.error(f"Content processing error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Content analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Content analysis failed")


@router.post("/analyze-file", response_model=Dict[str, Any])
async def analyze_file_content(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    content_analysis_service: ContentAnalysisService = Depends(
        get_content_analysis_service
    ),
    content_extraction_service: IContentExtractionService = Depends(
        get_content_extraction_service
    ),
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Analyze uploaded file content and return comprehensive analysis results."""
    try:
        with error_context(
            "analyze_file_api", user_id=current_user.user_id, filename=file.filename
        ):
            # Validate file
            if not file.filename:
                raise HTTPException(status_code=400, detail="No file provided")

            # Check file size (10MB limit)
            if file.size and file.size > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File too large (max 10MB)")

            # Extract content from file
            file_content = await file.read()

            try:
                extracted_content = await content_extraction_service.extract_content(
                    file_content, file.filename
                )
                content_text = extracted_content.get("text", "")
            except Exception as e:
                logger.error(f"Content extraction failed: {e}")
                raise HTTPException(
                    status_code=400, detail="Failed to extract content from file"
                )

            if not content_text or not content_text.strip():
                raise HTTPException(
                    status_code=400, detail="No extractable text content found in file"
                )

            # Analyze extracted content
            analysis = await content_analysis_service.analyze_content(
                content=content_text,
                title=title or file.filename,
                metadata={"filename": file.filename, "file_size": file.size},
            )

            return {
                "filename": file.filename,
                "content_type": analysis.content_type.value,
                "complexity_level": analysis.complexity_level.value,
                "technical_domains": analysis.technical_domains,
                "key_concepts": analysis.key_concepts,
                "readability_score": analysis.readability_score,
                "estimated_reading_time": analysis.estimated_reading_time,
                "language": analysis.language,
                "quality_score": analysis.quality_score,
                "tags": analysis.tags,
                "metadata": analysis.metadata,
                "extracted_content_preview": content_text[:500] + "..."
                if len(content_text) > 500
                else content_text,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File analysis failed: {e}")
        raise HTTPException(status_code=500, detail="File analysis failed")


@router.post("/batch-analyze", response_model=List[Dict[str, Any]])
async def batch_analyze_content(
    content_items: List[Dict[str, str]],
    content_analysis_service: ContentAnalysisService = Depends(
        get_content_analysis_service
    ),
    current_user: UserContext = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Analyze multiple content items in batch."""
    try:
        with error_context(
            "batch_analyze_api",
            user_id=current_user.user_id,
            batch_size=len(content_items),
        ):
            if not content_items:
                raise HTTPException(
                    status_code=400, detail="Content items list cannot be empty"
                )

            if len(content_items) > 50:  # Limit batch size
                raise HTTPException(
                    status_code=400, detail="Batch size too large (max 50 items)"
                )

            # Validate content items
            for i, item in enumerate(content_items):
                if not isinstance(item, dict):
                    raise HTTPException(
                        status_code=400, detail=f"Item {i} must be a dictionary"
                    )
                if "content" not in item:
                    raise HTTPException(
                        status_code=400, detail=f"Item {i} missing 'content' field"
                    )
                if not item["content"] or not item["content"].strip():
                    raise HTTPException(
                        status_code=400, detail=f"Item {i} has empty content"
                    )

            analyses = await content_analysis_service.batch_analyze_content(
                content_items
            )

            results = []
            for analysis in analyses:
                results.append(
                    {
                        "content_type": analysis.content_type.value,
                        "complexity_level": analysis.complexity_level.value,
                        "technical_domains": analysis.technical_domains,
                        "key_concepts": analysis.key_concepts,
                        "readability_score": analysis.readability_score,
                        "estimated_reading_time": analysis.estimated_reading_time,
                        "language": analysis.language,
                        "quality_score": analysis.quality_score,
                        "tags": analysis.tags,
                        "metadata": analysis.metadata,
                    }
                )

            return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Batch analysis failed")


@router.post("/extract-tags", response_model=Dict[str, List[str]])
async def extract_tags(
    content: str = Form(...),
    title: Optional[str] = Form(None),
    max_tags: Optional[int] = Form(20),
    content_analysis_service: ContentAnalysisService = Depends(
        get_content_analysis_service
    ),
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, List[str]]:
    """Extract tags from content without full analysis."""
    try:
        with error_context("extract_tags_api", user_id=current_user.user_id):
            if not content or not content.strip():
                raise HTTPException(status_code=400, detail="Content cannot be empty")

            if max_tags and (max_tags < 1 or max_tags > 50):
                raise HTTPException(
                    status_code=400, detail="max_tags must be between 1 and 50"
                )

            # Generate tags using the content analysis service
            tags = await content_analysis_service._generate_tags(content, title or "")

            # Limit tags if requested
            if max_tags:
                tags = tags[:max_tags]

            return {"tags": tags, "count": len(tags)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tag extraction failed: {e}")
        raise HTTPException(status_code=500, detail="Tag extraction failed")


@router.post("/classify-content", response_model=Dict[str, str])
async def classify_content(
    content: str = Form(...),
    title: Optional[str] = Form(None),
    content_analysis_service: ContentAnalysisService = Depends(
        get_content_analysis_service
    ),
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, str]:
    """Classify content type and complexity without full analysis."""
    try:
        with error_context("classify_content_api", user_id=current_user.user_id):
            if not content or not content.strip():
                raise HTTPException(status_code=400, detail="Content cannot be empty")

            # Classify content
            content_type = content_analysis_service._classify_content_type(
                content, title or ""
            )
            complexity_level = content_analysis_service._assess_complexity(content)
            technical_domains = content_analysis_service._identify_technical_domains(
                content
            )

            return {
                "content_type": content_type.value,
                "complexity_level": complexity_level.value,
                "primary_domain": technical_domains[0]
                if technical_domains
                else "General",
                "all_domains": ", ".join(technical_domains)
                if technical_domains
                else "General",
            }

    except Exception as e:
        logger.error(f"Content classification failed: {e}")
        raise HTTPException(status_code=500, detail="Content classification failed")


@router.get("/content-types", response_model=List[str])
async def get_content_types(
    current_user: UserContext = Depends(get_current_user),
) -> List[str]:
    """Get list of available content types."""
    from ...services.content_analysis import ContentType

    return [content_type.value for content_type in ContentType]


@router.get("/complexity-levels", response_model=List[str])
async def get_complexity_levels(
    current_user: UserContext = Depends(get_current_user),
) -> List[str]:
    """Get list of available complexity levels."""
    from ...services.content_analysis import ComplexityLevel

    return [level.value for level in ComplexityLevel]


@router.get("/technical-domains", response_model=List[str])
async def get_technical_domains(
    content_analysis_service: ContentAnalysisService = Depends(
        get_content_analysis_service
    ),
    current_user: UserContext = Depends(get_current_user),
) -> List[str]:
    """Get list of available technical domains."""
    domains = list(content_analysis_service.domain_keywords.keys())
    return [domain.replace("_", " ").title() for domain in domains]
