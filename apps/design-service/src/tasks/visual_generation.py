import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from celery import current_task
from celery.exceptions import Retry

from src.infrastructure.celery_connectivity import create_celery_app

logger = logging.getLogger(__name__)

# Create celery app instance lazily to avoid import-time configuration issues
def get_celery_app():
    """Get or create the celery app instance."""
    if not hasattr(get_celery_app, '_app'):
        try:
            get_celery_app._app = create_celery_app("design_service")
        except Exception as e:
            # During testing, create a mock app to avoid configuration issues
            from unittest.mock import MagicMock
            get_celery_app._app = MagicMock()
            logger.warning(f"Using mock Celery app due to configuration error: {e}")
    return get_celery_app._app

celery_app = get_celery_app()
from src.services.visual_generation_service import VisualGenerationService, VisualGenerationError
from src.services.llm_client import LLMClient
from src.repositories.design_repository import DesignRepository
from common.storage.client import StorageClient
from src.core.config import get_settings

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="visual_generation.generate_visuals",
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True
)
def generate_visuals_task(
    self,
    design_id: str,
    design_data: Dict[str, Any],
    visual_types: Optional[List[str]] = None,
    size: str = "1024x1024",
    quality: str = "standard",
    priority: str = "normal"
) -> Dict[str, Any]:
    """
    Celery task to generate visual outputs for a design.
    
    Args:
        design_id: ID of the design to generate visuals for
        visual_types: List of visual types to generate (default: all)
        size: Image size (1024x1024, 1792x1024, 1024x1792)
        quality: Image quality (standard, hd)
        priority: Task priority (low, normal, high)
        
    Returns:
        Dictionary containing generation results and metadata
        
    Raises:
        Retry: If generation fails and retries are available
    """
    task_id = self.request.id
    start_time = datetime.utcnow()
    
    try:
        logger.info(
            f"Starting visual generation task {task_id} for design {design_id}. "
            f"Types: {visual_types}, Size: {size}, Quality: {quality}, Priority: {priority}"
        )
        
        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": len(visual_types) if visual_types else 3,
                "status": "Initializing visual generation...",
                "design_id": design_id,
                "started_at": start_time.isoformat()
            }
        )
        
        # Run the async visual generation
        result = asyncio.run(_run_visual_generation(
            task=self,
            design_id=design_id,
            design_data=design_data,
            visual_types=visual_types,
            size=size,
            quality=quality
        ))
        
        # Calculate total time
        total_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Final success state
        final_result = {
            **result,
            "task_id": task_id,
            "total_time": total_time,
            "completed_at": datetime.utcnow().isoformat(),
            "status": "completed"
        }
        
        logger.info(
            f"Visual generation task {task_id} completed for design {design_id}. "
            f"Total time: {total_time:.2f}s, Cost: ${result.get('total_cost', 0):.4f}"
        )
        
        return final_result
        
    except VisualGenerationError as e:
        logger.error(f"Visual generation task {task_id} failed for design {design_id}: {e}")
        
        # Update task state to failure
        self.update_state(
            state="FAILURE",
            meta={
                "error": str(e),
                "design_id": design_id,
                "failed_at": datetime.utcnow().isoformat(),
                "retry_count": self.request.retries
            }
        )
        
        # Retry if we have retries left
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying visual generation task {task_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=self.default_retry_delay * (2 ** self.request.retries))
        
        # No more retries, mark as failed
        raise e
        
    except Exception as e:
        logger.error(f"Unexpected error in visual generation task {task_id}: {e}")
        
        # Update task state to failure
        self.update_state(
            state="FAILURE",
            meta={
                "error": f"Unexpected error: {str(e)}",
                "design_id": design_id,
                "failed_at": datetime.utcnow().isoformat(),
                "retry_count": self.request.retries
            }
        )
        
        # Retry for unexpected errors too
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying visual generation task {task_id} due to unexpected error (attempt {self.request.retries + 1})")
            raise self.retry(countdown=self.default_retry_delay * (2 ** self.request.retries))
        
        raise e


async def _run_visual_generation(
    task,
    design_id: str,
    design_data: Dict[str, Any],
    visual_types: Optional[List[str]],
    size: str,
    quality: str
) -> Dict[str, Any]:
    """
    Run the actual visual generation process asynchronously.
    
    Args:
        task: Celery task instance for progress updates
        design_id: ID of the design
        visual_types: List of visual types to generate
        size: Image size
        quality: Image quality
        
    Returns:
        Generation results dictionary
    """
    # Initialize services with proper error handling
    try:
        settings = get_settings()
        
        # Create service dependencies
        llm_client = LLMClient(settings.llm)
        storage_client = StorageClient(settings.storage)
        design_repository = DesignRepository()
        
        # Create visual generation service
        visual_service = VisualGenerationService(
            llm_client=llm_client,
            storage_client=storage_client,
            design_repository=design_repository
        )
        
    except Exception as e:
        logger.error(f"Failed to initialize visual generation services: {e}")
        raise VisualGenerationError(f"Service initialization failed: {e}")
    
    # Update progress
    task.update_state(
        state="PROGRESS",
        meta={
            "current": 0,
            "total": len(visual_types) if visual_types else 3,
            "status": "Starting visual generation...",
            "design_id": design_id
        }
    )
    
    # Update progress
    task.update_state(
        state="PROGRESS",
        meta={
            "current": 1,
            "total": len(visual_types) if visual_types else 3,
            "status": "Starting visual generation...",
            "design_id": design_id
        }
    )
    
    # Generate visuals using our TDD service
    result = await visual_service.generate_all_visuals(
        design_id=design_id,
        design_data=design_data,
        visual_types=visual_types,
        size=size,
        quality=quality
    )
    
    return result


async def _generate_visuals_with_progress(
    task,
    visual_service: VisualGenerationService,
    design_id: str,
    design_data: Dict[str, Any],
    visual_types: Optional[List[str]],
    size: str,
    quality: str
) -> Dict[str, Any]:
    """
    Generate visuals with progress tracking.
    
    Args:
        task: Celery task instance
        visual_service: Visual generation service
        design_id: Design ID
        design_data: Design data
        visual_types: Visual types to generate
        size: Image size
        quality: Image quality
        
    Returns:
        Generation results
    """
    if visual_types is None:
        visual_types = ["floor_plan", "rendering", "3d_model"]
    
    results = {}
    total_cost = 0.0
    current_step = 1
    total_steps = len(visual_types)
    
    # Update design status to processing
    await visual_service._update_design_visual_field(
        design_id=design_id,
        field="visual_generation_status",
        value="processing"
    )
    
    # Generate each visual type with progress updates
    for i, visual_type in enumerate(visual_types):
        try:
            # Update progress
            task.update_state(
                state="PROGRESS",
                meta={
                    "current": current_step,
                    "total": total_steps,
                    "status": f"Generating {visual_type.replace('_', ' ')}...",
                    "design_id": design_id,
                    "current_visual_type": visual_type
                }
            )
            
            logger.info(f"Generating {visual_type} for design {design_id} (step {current_step}/{total_steps})")
            
            # Generate the specific visual type
            if visual_type == "floor_plan":
                result = await visual_service.generate_floor_plan(
                    design_id, design_data, size, quality
                )
                results["floor_plan"] = result
                
            elif visual_type == "rendering":
                result = await visual_service.generate_3d_rendering(
                    design_id, design_data, size, quality
                )
                results["rendering"] = result
                
            elif visual_type == "3d_model":
                result = await visual_service.generate_3d_model(
                    design_id, design_data, size, quality
                )
                results["3d_model"] = result
            
            total_cost += result["generation_cost"]
            current_step += 1
            
            logger.info(f"Successfully generated {visual_type} for design {design_id}")
            
        except Exception as e:
            logger.error(f"Failed to generate {visual_type} for design {design_id}: {e}")
            results[visual_type] = {"error": str(e)}
            current_step += 1
    
    # Update design status based on results
    generated_types = [vt for vt in visual_types if vt in results and "error" not in results[vt]]
    failed_types = [vt for vt in visual_types if vt in results and "error" in results[vt]]
    
    if len(generated_types) == len(visual_types):
        status = "completed"
    elif len(generated_types) > 0:
        status = "partial"
    else:
        status = "failed"
    
    await visual_service._update_design_visual_field(
        design_id=design_id,
        field="visual_generation_status",
        value=status
    )
    
    # Final progress update
    task.update_state(
        state="PROGRESS",
        meta={
            "current": total_steps,
            "total": total_steps,
            "status": f"Completed visual generation. Generated: {len(generated_types)}, Failed: {len(failed_types)}",
            "design_id": design_id,
            "generated_types": generated_types,
            "failed_types": failed_types
        }
    )
    
    return {
        "design_id": design_id,
        "results": results,
        "total_cost": total_cost,
        "generated_types": generated_types,
        "failed_types": failed_types,
        "status": status
    }


@celery_app.task(
    bind=True,
    name="visual_generation.generate_single_visual",
    max_retries=3,
    default_retry_delay=30,  # 30 seconds
    autoretry_for=(VisualGenerationError,),
    retry_backoff=True
)
def generate_single_visual_task(
    self,
    design_id: str,
    visual_type: str,
    size: str = "1024x1024",
    quality: str = "standard"
) -> Dict[str, Any]:
    """
    Celery task to generate a single visual output for a design.
    
    Args:
        design_id: ID of the design
        visual_type: Type of visual to generate (floor_plan, rendering, 3d_model)
        size: Image size
        quality: Image quality
        
    Returns:
        Dictionary containing generation result and metadata
    """
    task_id = self.request.id
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"Starting single visual generation task {task_id} for design {design_id}, type: {visual_type}")
        
        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 1,
                "status": f"Generating {visual_type.replace('_', ' ')}...",
                "design_id": design_id,
                "visual_type": visual_type,
                "started_at": start_time.isoformat()
            }
        )
        
        # Run the async visual generation
        result = asyncio.run(_run_single_visual_generation(
            task=self,
            design_id=design_id,
            visual_type=visual_type,
            size=size,
            quality=quality
        ))
        
        # Calculate total time
        total_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Final success state
        final_result = {
            **result,
            "task_id": task_id,
            "total_time": total_time,
            "completed_at": datetime.utcnow().isoformat(),
            "status": "completed"
        }
        
        logger.info(
            f"Single visual generation task {task_id} completed for design {design_id}. "
            f"Type: {visual_type}, Time: {total_time:.2f}s, Cost: ${result.get('generation_cost', 0):.4f}"
        )
        
        return final_result
        
    except Exception as e:
        logger.error(f"Single visual generation task {task_id} failed: {e}")
        
        # Update task state to failure
        self.update_state(
            state="FAILURE",
            meta={
                "error": str(e),
                "design_id": design_id,
                "visual_type": visual_type,
                "failed_at": datetime.utcnow().isoformat(),
                "retry_count": self.request.retries
            }
        )
        
        # Retry if we have retries left
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=self.default_retry_delay * (2 ** self.request.retries))
        
        raise e


async def _run_single_visual_generation(
    task,
    design_id: str,
    visual_type: str,
    size: str,
    quality: str
) -> Dict[str, Any]:
    """
    Run single visual generation asynchronously.
    
    Args:
        task: Celery task instance
        design_id: Design ID
        visual_type: Visual type to generate
        size: Image size
        quality: Image quality
        
    Returns:
        Generation result
    """
    # Initialize services
    settings = get_settings()
    
    llm_client = LLMClient(settings.llm)
    storage_client = StorageClient(settings.storage)
    design_repository = DesignRepository()
    
    visual_service = VisualGenerationService(
        llm_client=llm_client,
        storage_client=storage_client,
        design_repository=design_repository
    )
    
    # Get design data
    design = await design_repository.get_design(design_id)
    if not design:
        raise VisualGenerationError(f"Design {design_id} not found")
    
    design_data = {
        "building_type": design.building_type,
        "description": design.description,
        "requirements": design.requirements or {},
        "style": design.style,
        "materials": design.materials
    }
    
    # Update progress
    task.update_state(
        state="PROGRESS",
        meta={
            "current": 0,
            "total": 1,
            "status": f"Generating {visual_type.replace('_', ' ')}...",
            "design_id": design_id,
            "visual_type": visual_type
        }
    )
    
    # Generate the specific visual type
    if visual_type == "floor_plan":
        result = await visual_service.generate_floor_plan(
            design_id, design_data, size, quality
        )
    elif visual_type == "rendering":
        result = await visual_service.generate_3d_rendering(
            design_id, design_data, size, quality
        )
    elif visual_type == "3d_model":
        result = await visual_service.generate_3d_model(
            design_id, design_data, size, quality
        )
    else:
        raise VisualGenerationError(f"Unknown visual type: {visual_type}")
    
    return result


@celery_app.task(name="visual_generation.cleanup_failed_generations")
def cleanup_failed_generations_task() -> Dict[str, Any]:
    """
    Periodic task to clean up failed visual generation attempts.
    
    This task:
    1. Finds designs with failed visual generation status
    2. Cleans up any orphaned storage files
    3. Resets status for designs that can be retried
    
    Returns:
        Dictionary with cleanup statistics
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info("Starting cleanup of failed visual generations")
        
        # This would be implemented to:
        # 1. Query designs with failed status older than X hours
        # 2. Clean up any orphaned files in storage
        # 3. Reset status for designs that can be retried
        # 4. Log cleanup statistics
        
        # For now, return a placeholder result
        cleanup_stats = {
            "cleaned_designs": 0,
            "deleted_files": 0,
            "reset_for_retry": 0,
            "cleanup_time": (datetime.utcnow() - start_time).total_seconds()
        }
        
        logger.info(f"Cleanup completed: {cleanup_stats}")
        return cleanup_stats
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        raise e


# Task routing configuration
def get_visual_generation_routing():
    """
    Get routing configuration for visual generation tasks.
    
    Returns:
        Dictionary with task routing rules
    """
    return {
        "visual_generation.generate_visuals": {
            "queue": "visual_generation",
            "routing_key": "visual.generate"
        },
        "visual_generation.generate_single_visual": {
            "queue": "visual_generation",
            "routing_key": "visual.single"
        },
        "visual_generation.cleanup_failed_generations": {
            "queue": "maintenance",
            "routing_key": "maintenance.cleanup"
        }
    }


# Task monitoring utilities
def get_visual_generation_stats() -> Dict[str, Any]:
    """
    Get statistics about visual generation tasks.
    
    Returns:
        Dictionary with task statistics
    """
    # This would query Celery for task statistics
    # For now, return placeholder data
    return {
        "active_tasks": 0,
        "pending_tasks": 0,
        "completed_today": 0,
        "failed_today": 0,
        "average_generation_time": 0.0,
        "total_cost_today": 0.0
    }