"""
Enhanced resource processing service with integrated content analysis.

This service handles the complete resource processing pipeline including
content extraction, analysis, tagging, and vector indexing.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..core.error_handling import (ErrorRecovery, error_context,
                                   handle_service_errors)
from ..exceptions import ContentProcessingError, ResourceProcessingError
from ..models.resource import Resource
from ..services.content_analysis import ContentAnalysis, ContentAnalysisService
from ..services.content_extraction import IContentExtractionService
from ..services.llm import ILLMService
from ..services.vector_search import IVectorSearchService

logger = logging.getLogger(__name__)


class EnhancedResourceProcessingService:
    """Service for enhanced resource processing with content analysis."""

    def __init__(
        self,
        content_extraction_service: IContentExtractionService,
        content_analysis_service: ContentAnalysisService,
        vector_search_service: IVectorSearchService,
        llm_service: ILLMService,
    ):
        """Initialize enhanced resource processing service.

        Args:
            content_extraction_service: Service for content extraction
            content_analysis_service: Service for content analysis
            vector_search_service: Service for vector search
            llm_service: Service for LLM operations
        """
        self.content_extraction = content_extraction_service
        self.content_analysis = content_analysis_service
        self.vector_search = vector_search_service
        self.llm_service = llm_service

    @handle_service_errors("enhanced_resource_processing", "process_resource")
    async def process_resource_with_analysis(
        self,
        resource: Resource,
        file_content: bytes,
        db: Session,
        force_reanalysis: bool = False,
    ) -> Dict[str, Any]:
        """Process a resource with comprehensive content analysis.

        Args:
            resource: Resource model instance
            file_content: Raw file content bytes
            db: Database session
            force_reanalysis: Whether to force re-analysis even if already analyzed

        Returns:
            Dictionary with processing results
        """
        with error_context(
            "process_resource_with_analysis",
            resource_id=resource.id,
            resource_title=resource.title,
        ):
            processing_results = {
                "resource_id": resource.id,
                "steps_completed": [],
                "errors": [],
                "analysis_results": None,
                "vector_indexed": False,
                "content_extracted": False,
            }

            try:
                # Step 1: Extract content from file
                logger.info(f"Extracting content from resource {resource.id}")
                extracted_content = await self.content_extraction.extract_content(
                    file_content, resource.storage_path
                )

                if not extracted_content or not extracted_content.get("text"):
                    raise ResourceProcessingError(
                        "Failed to extract text content from file"
                    )

                content_text = extracted_content["text"]
                processing_results["content_extracted"] = True
                processing_results["steps_completed"].append("content_extraction")

                # Step 2: Check if analysis is needed
                needs_analysis = (
                    force_reanalysis
                    or not resource.analysis_timestamp
                    or not resource.content_classification
                )

                if needs_analysis:
                    # Step 3: Perform content analysis
                    logger.info(f"Analyzing content for resource {resource.id}")
                    analysis = await self.content_analysis.analyze_content(
                        content=content_text,
                        title=resource.title,
                        metadata={
                            "resource_id": resource.id,
                            "content_type": resource.content_type,
                            "file_size": resource.file_size,
                            "author": resource.author,
                            "publication_date": resource.publication_date.isoformat()
                            if resource.publication_date
                            else None,
                        },
                    )

                    # Step 4: Update resource with analysis results
                    await self._update_resource_with_analysis(resource, analysis, db)
                    processing_results["analysis_results"] = self._analysis_to_dict(
                        analysis
                    )
                    processing_results["steps_completed"].append("content_analysis")

                    logger.info(
                        f"Content analysis completed for resource {resource.id}"
                    )
                else:
                    logger.info(
                        f"Skipping analysis for resource {resource.id} (already analyzed)"
                    )
                    processing_results["steps_completed"].append("analysis_skipped")

                # Step 5: Generate enhanced summary and takeaways if not present
                if not resource.summary or force_reanalysis:
                    try:
                        summary = await self.llm_service.generate_summary(content_text)
                        key_takeaways = await self.llm_service.extract_key_takeaways(
                            content_text
                        )

                        resource.summary = summary
                        resource.key_takeaways = key_takeaways
                        processing_results["steps_completed"].append(
                            "summary_generation"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to generate summary for resource {resource.id}: {e}"
                        )
                        processing_results["errors"].append(
                            f"Summary generation failed: {str(e)}"
                        )

                # Step 6: Index in vector search
                try:
                    await self.vector_search.index_resource(
                        resource_id=resource.id,
                        title=resource.title,
                        description=resource.description,
                        content=content_text,
                        metadata={
                            "content_type": resource.content_type,
                            "content_classification": resource.content_classification,
                            "complexity_level": resource.complexity_level,
                            "technical_domains": resource.technical_domains or [],
                            "auto_tags": resource.auto_tags or [],
                            "author": resource.author,
                            "language": resource.language,
                            "quality_score": resource.quality_score,
                        },
                    )
                    processing_results["vector_indexed"] = True
                    processing_results["steps_completed"].append("vector_indexing")
                    logger.info(f"Vector indexing completed for resource {resource.id}")
                except Exception as e:
                    logger.error(
                        f"Vector indexing failed for resource {resource.id}: {e}"
                    )
                    processing_results["errors"].append(
                        f"Vector indexing failed: {str(e)}"
                    )

                # Step 7: Commit database changes
                db.commit()
                processing_results["steps_completed"].append("database_commit")

                logger.info(
                    f"Enhanced resource processing completed for resource {resource.id}"
                )
                return processing_results

            except Exception as e:
                logger.error(
                    f"Enhanced resource processing failed for resource {resource.id}: {e}"
                )
                db.rollback()
                processing_results["errors"].append(f"Processing failed: {str(e)}")
                raise ResourceProcessingError(
                    f"Enhanced resource processing failed: {str(e)}"
                )

    async def _update_resource_with_analysis(
        self, resource: Resource, analysis: ContentAnalysis, db: Session
    ) -> None:
        """Update resource with content analysis results."""
        try:
            resource.content_classification = analysis.content_type.value
            resource.complexity_level = analysis.complexity_level.value
            resource.technical_domains = analysis.technical_domains
            resource.readability_score = analysis.readability_score
            resource.estimated_reading_time = analysis.estimated_reading_time
            resource.language = analysis.language
            resource.quality_score = analysis.quality_score
            resource.auto_tags = analysis.tags
            resource.analysis_metadata = analysis.metadata
            resource.analysis_timestamp = datetime.utcnow()

            # Also update keywords if not already set
            if not resource.keywords and analysis.key_concepts:
                resource.keywords = analysis.key_concepts

            logger.debug(f"Updated resource {resource.id} with analysis results")

        except Exception as e:
            logger.error(f"Failed to update resource {resource.id} with analysis: {e}")
            raise ResourceProcessingError(
                f"Failed to update resource with analysis: {str(e)}"
            )

    def _analysis_to_dict(self, analysis: ContentAnalysis) -> Dict[str, Any]:
        """Convert ContentAnalysis to dictionary."""
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

    @handle_service_errors("enhanced_resource_processing", "batch_process")
    async def batch_process_resources(
        self, resource_ids: List[int], db: Session, force_reanalysis: bool = False
    ) -> Dict[str, Any]:
        """Process multiple resources in batch with content analysis.

        Args:
            resource_ids: List of resource IDs to process
            db: Database session
            force_reanalysis: Whether to force re-analysis

        Returns:
            Dictionary with batch processing results
        """
        with error_context("batch_process_resources", batch_size=len(resource_ids)):
            batch_results = {
                "total_resources": len(resource_ids),
                "processed_successfully": 0,
                "failed_resources": [],
                "processing_errors": [],
                "start_time": datetime.utcnow().isoformat(),
            }

            for resource_id in resource_ids:
                try:
                    # Get resource from database
                    resource = (
                        db.query(Resource).filter(Resource.id == resource_id).first()
                    )
                    if not resource:
                        batch_results["failed_resources"].append(resource_id)
                        batch_results["processing_errors"].append(
                            f"Resource {resource_id} not found"
                        )
                        continue

                    # Read file content
                    try:
                        with open(resource.storage_path, "rb") as f:
                            file_content = f.read()
                    except Exception as e:
                        batch_results["failed_resources"].append(resource_id)
                        batch_results["processing_errors"].append(
                            f"Failed to read file for resource {resource_id}: {str(e)}"
                        )
                        continue

                    # Process resource
                    await self.process_resource_with_analysis(
                        resource=resource,
                        file_content=file_content,
                        db=db,
                        force_reanalysis=force_reanalysis,
                    )

                    batch_results["processed_successfully"] += 1
                    logger.info(
                        f"Successfully processed resource {resource_id} in batch"
                    )

                except Exception as e:
                    batch_results["failed_resources"].append(resource_id)
                    batch_results["processing_errors"].append(
                        f"Resource {resource_id}: {str(e)}"
                    )
                    logger.error(
                        f"Failed to process resource {resource_id} in batch: {e}"
                    )

            batch_results["end_time"] = datetime.utcnow().isoformat()
            batch_results["success_rate"] = (
                batch_results["processed_successfully"]
                / batch_results["total_resources"]
                if batch_results["total_resources"] > 0
                else 0
            )

            logger.info(
                f"Batch processing completed: {batch_results['processed_successfully']}/{batch_results['total_resources']} resources processed successfully"
            )

            return batch_results

    @handle_service_errors("enhanced_resource_processing", "reanalyze_resource")
    async def reanalyze_resource(self, resource_id: int, db: Session) -> Dict[str, Any]:
        """Re-analyze a specific resource with latest analysis algorithms.

        Args:
            resource_id: ID of resource to re-analyze
            db: Database session

        Returns:
            Dictionary with re-analysis results
        """
        with error_context("reanalyze_resource", resource_id=resource_id):
            # Get resource
            resource = db.query(Resource).filter(Resource.id == resource_id).first()
            if not resource:
                raise ResourceProcessingError(f"Resource {resource_id} not found")

            # Read file content
            try:
                with open(resource.storage_path, "rb") as f:
                    file_content = f.read()
            except Exception as e:
                raise ResourceProcessingError(
                    f"Failed to read file for resource {resource_id}: {str(e)}"
                )

            # Process with forced re-analysis
            return await self.process_resource_with_analysis(
                resource=resource,
                file_content=file_content,
                db=db,
                force_reanalysis=True,
            )

    async def get_analysis_summary(
        self, resource_ids: Optional[List[int]] = None, db: Session = None
    ) -> Dict[str, Any]:
        """Get summary of content analysis across resources.

        Args:
            resource_ids: Optional list of specific resource IDs
            db: Database session

        Returns:
            Dictionary with analysis summary statistics
        """
        try:
            query = db.query(Resource)
            if resource_ids:
                query = query.filter(Resource.id.in_(resource_ids))

            resources = query.all()

            if not resources:
                return {"message": "No resources found"}

            # Calculate statistics
            total_resources = len(resources)
            analyzed_resources = len([r for r in resources if r.analysis_timestamp])

            content_types = {}
            complexity_levels = {}
            languages = {}
            technical_domains = {}

            total_reading_time = 0
            quality_scores = []
            readability_scores = []

            for resource in resources:
                if resource.analysis_timestamp:
                    # Content types
                    if resource.content_classification:
                        content_types[resource.content_classification] = (
                            content_types.get(resource.content_classification, 0) + 1
                        )

                    # Complexity levels
                    if resource.complexity_level:
                        complexity_levels[resource.complexity_level] = (
                            complexity_levels.get(resource.complexity_level, 0) + 1
                        )

                    # Languages
                    if resource.language:
                        languages[resource.language] = (
                            languages.get(resource.language, 0) + 1
                        )

                    # Technical domains
                    if resource.technical_domains:
                        for domain in resource.technical_domains:
                            technical_domains[domain] = (
                                technical_domains.get(domain, 0) + 1
                            )

                    # Metrics
                    if resource.estimated_reading_time:
                        total_reading_time += resource.estimated_reading_time

                    if resource.quality_score is not None:
                        quality_scores.append(resource.quality_score)

                    if resource.readability_score is not None:
                        readability_scores.append(resource.readability_score)

            # Calculate averages
            avg_quality_score = (
                sum(quality_scores) / len(quality_scores) if quality_scores else 0
            )
            avg_readability_score = (
                sum(readability_scores) / len(readability_scores)
                if readability_scores
                else 0
            )

            return {
                "total_resources": total_resources,
                "analyzed_resources": analyzed_resources,
                "analysis_coverage": analyzed_resources / total_resources
                if total_resources > 0
                else 0,
                "content_type_distribution": content_types,
                "complexity_distribution": complexity_levels,
                "language_distribution": languages,
                "top_technical_domains": dict(
                    sorted(technical_domains.items(), key=lambda x: x[1], reverse=True)[
                        :10
                    ]
                ),
                "total_estimated_reading_time": total_reading_time,
                "average_quality_score": round(avg_quality_score, 2),
                "average_readability_score": round(avg_readability_score, 2),
                "quality_score_range": {
                    "min": min(quality_scores) if quality_scores else 0,
                    "max": max(quality_scores) if quality_scores else 0,
                },
                "readability_score_range": {
                    "min": min(readability_scores) if readability_scores else 0,
                    "max": max(readability_scores) if readability_scores else 0,
                },
            }

        except Exception as e:
            logger.error(f"Failed to get analysis summary: {e}")
            raise ResourceProcessingError(f"Failed to get analysis summary: {str(e)}")


def get_enhanced_resource_processing_service(
    content_extraction_service: IContentExtractionService,
    content_analysis_service: ContentAnalysisService,
    vector_search_service: IVectorSearchService,
    llm_service: ILLMService,
) -> EnhancedResourceProcessingService:
    """Get enhanced resource processing service instance."""
    return EnhancedResourceProcessingService(
        content_extraction_service=content_extraction_service,
        content_analysis_service=content_analysis_service,
        vector_search_service=vector_search_service,
        llm_service=llm_service,
    )
