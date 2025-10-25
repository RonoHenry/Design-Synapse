"""
Task status tracking API endpoints.

This module provides endpoints for tracking the status of asynchronous tasks,
particularly visual generation tasks. It integrates with Celery to provide
real-time task status, progress, and results.

Endpoints:
- GET /api/v1/tasks/{task_id} - Get task status and results

Requirements:
- 5: Task status tracking and monitoring
- 8: Asynchronous task processing
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

try:
    from src.tasks import celery_app
except Exception:
    # For testing when Celery is not configured
    celery_app = None
from src.api.dependencies import CurrentUserId

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskStatusResponse(BaseModel):
    """Response schema for task status information."""
    
    task_id: str = Field(..., description="Unique task identifier")
    state: str = Field(..., description="Current task state (PENDING, PROGRESS, SUCCESS, FAILURE, RETRY, REVOKED)")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result data (available when completed)")
    progress: float = Field(0, description="Task progress percentage (0-100)")
    current_step: Optional[str] = Field(None, description="Current processing step")
    message: Optional[str] = Field(None, description="Current status message")
    error: Optional[str] = Field(None, description="Error message (if failed)")
    retry_count: Optional[int] = Field(None, description="Number of retry attempts")
    max_retries: Optional[int] = Field(None, description="Maximum retry attempts")
    next_retry: Optional[str] = Field(None, description="Next retry timestamp (ISO format)")
    created_at: str = Field(..., description="Task creation timestamp (ISO format)")
    completed_at: Optional[str] = Field(None, description="Task completion timestamp (ISO format)")
    execution_time_seconds: Optional[float] = Field(None, description="Task execution time in seconds")
    worker_info: Dict[str, Any] = Field(default_factory=dict, description="Worker information")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional task metadata")


def validate_task_id(task_id: str) -> str:
    """
    Validate task ID format.
    
    Args:
        task_id: Task ID to validate
        
    Returns:
        Validated task ID
        
    Raises:
        HTTPException: If task ID format is invalid
    """
    try:
        # Check if it's a valid UUID format
        uuid.UUID(task_id)
        return task_id
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task ID format. Task ID must be a valid UUID."
        )


def get_task_status_from_celery(task_id: str) -> Dict[str, Any]:
    """
    Get task status from Celery.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Dictionary containing task status information
        
    Raises:
        Exception: If Celery connection fails
    """
    try:
        # Check if Celery is available
        if celery_app is None:
            raise Exception("Celery not configured")
            
        # Get task result from Celery
        task_result = AsyncResult(task_id, app=celery_app)
        
        # Base task information
        task_info = {
            "task_id": task_id,
            "state": task_result.state,
            "result": None,
            "progress": 0,
            "current_step": None,
            "message": None,
            "error": None,
            "retry_count": None,
            "max_retries": None,
            "next_retry": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "execution_time_seconds": None,
            "worker_info": {},
            "metadata": {}
        }
        
        # Handle different task states
        if task_result.state == "PENDING":
            # Task is waiting to be processed or doesn't exist
            task_info["message"] = "Task is pending or not found"
            task_info["progress"] = 0
            
        elif task_result.state == "PROGRESS":
            # Task is in progress
            if task_result.info:
                task_info["progress"] = task_result.info.get("progress", 0)
                task_info["current_step"] = task_result.info.get("current_step")
                task_info["message"] = task_result.info.get("message")
                task_info["retry_count"] = task_result.info.get("retry_count")
                task_info["max_retries"] = task_result.info.get("max_retries")
            
        elif task_result.state == "SUCCESS":
            # Task completed successfully
            task_info["result"] = task_result.result
            task_info["progress"] = 100
            task_info["message"] = "Task completed successfully"
            
            # Add completion timestamp if available
            if hasattr(task_result, 'date_done') and task_result.date_done:
                # Convert to string to handle Mock objects
                date_done = str(task_result.date_done) if task_result.date_done else None
                if date_done and not date_done.startswith('<Mock'):
                    task_info["completed_at"] = date_done
                
        elif task_result.state == "FAILURE":
            # Task failed
            task_info["error"] = str(task_result.result) if task_result.result else "Task failed"
            task_info["progress"] = 0
            task_info["message"] = "Task failed"
            
            # Add traceback if available
            if hasattr(task_result, 'traceback') and task_result.traceback:
                task_info["metadata"]["traceback"] = task_result.traceback
                
        elif task_result.state == "RETRY":
            # Task is being retried
            if task_result.info:
                task_info["retry_count"] = task_result.info.get("retry_count", 0)
                task_info["max_retries"] = task_result.info.get("max_retries", 3)
                task_info["next_retry"] = task_result.info.get("next_retry")
                task_info["error"] = str(task_result.result) if task_result.result else "Task retry"
            task_info["message"] = "Task is being retried"
            
        elif task_result.state == "REVOKED":
            # Task was cancelled/revoked
            task_info["message"] = "Task was cancelled"
            task_info["progress"] = 0
        
        # Add metadata if available (safely handle Mock objects in tests)
        if hasattr(task_result, 'name') and task_result.name:
            # Convert to string to handle Mock objects
            task_name = str(task_result.name) if task_result.name else None
            if task_name and not task_name.startswith('<Mock'):
                task_info["metadata"]["task_name"] = task_name
            
        if hasattr(task_result, 'date_done') and task_result.date_done:
            # Convert to string to handle Mock objects
            date_done = str(task_result.date_done) if task_result.date_done else None
            if date_done and not date_done.startswith('<Mock'):
                task_info["metadata"]["completed_at"] = date_done
            
        # Calculate execution time for completed tasks
        if task_result.state in ["SUCCESS", "FAILURE"] and task_info.get("completed_at"):
            try:
                # This is a simplified calculation - in practice you'd store start time
                task_info["execution_time_seconds"] = 0.0  # Placeholder
            except Exception:
                pass
        
        return task_info
        
    except Exception as e:
        logger.error(f"Error getting task status from Celery: {e}")
        raise


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user_id: CurrentUserId,
) -> TaskStatusResponse:
    """
    Get the status of an asynchronous task.
    
    This endpoint allows clients to check the status of long-running tasks,
    particularly visual generation tasks. It provides real-time information
    about task progress, results, and any errors that may have occurred.
    
    Args:
        task_id: Unique identifier of the task to check
        current_user_id: ID of the authenticated user
        
    Returns:
        TaskStatusResponse containing current task status and metadata
        
    Raises:
        HTTPException: 
            - 400 if task ID format is invalid
            - 401 if user is not authenticated
            - 408 if task status check times out
            - 503 if task queue service is unavailable
            - 500 for internal server errors
    """
    # Validate task ID format
    validated_task_id = validate_task_id(task_id)
    
    try:
        logger.info(f"Getting task status for task {validated_task_id} (user: {current_user_id})")
        
        # Get task status from Celery
        task_info = get_task_status_from_celery(validated_task_id)
        
        # Create response
        response = TaskStatusResponse(**task_info)
        
        logger.debug(f"Task {validated_task_id} status: {response.state}")
        return response
        
    except TimeoutError as e:
        logger.warning(f"Task status check timeout for {validated_task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Task status check timeout. Please try again."
        )
        
    except Exception as e:
        error_msg = str(e)
        
        # Check for specific Celery connection errors
        if "connection" in error_msg.lower() or "broker" in error_msg.lower():
            logger.error(f"Task queue service unavailable: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Task queue service unavailable. Please try again later."
            )
        
        # Generic error handling
        logger.error(f"Error getting task status for {validated_task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving task status."
        )