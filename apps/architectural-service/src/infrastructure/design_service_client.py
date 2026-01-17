"""
Design Service client for visual rendering and generation.
"""

import logging
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from pydantic import BaseModel

# Add workspace root to path for common packages
workspace_root = Path(__file__).parent.parent.parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from packages.common.resilience.circuit_breaker import (CircuitBreaker,
                                                        CircuitBreakerConfig)
from packages.common.resilience.retry import RetryConfig, retry_async_call

logger = logging.getLogger(__name__)


class RenderType(str, Enum):
    """Types of rendering outputs."""

    FLOOR_PLAN = "floor_plan"
    ELEVATION = "elevation"
    SECTION = "section"
    THREE_D_VIEW = "3d_view"
    WALKTHROUGH = "walkthrough"


class RenderStatus(str, Enum):
    """Rendering job status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class RenderParameters(BaseModel):
    """Parameters for rendering request."""

    render_type: RenderType
    resolution: Optional[str] = "1920x1080"
    quality: Optional[str] = "high"
    camera_angle: Optional[Dict[str, float]] = None
    lighting: Optional[str] = "natural"
    materials: Optional[bool] = True
    annotations: Optional[bool] = False
    metadata: Dict[str, Any] = {}


class RenderJob(BaseModel):
    """Rendering job information."""

    job_id: UUID
    design_id: UUID
    render_type: RenderType
    status: RenderStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class VisualOutput(BaseModel):
    """Visual rendering output."""

    output_id: UUID
    job_id: UUID
    render_type: RenderType
    file_url: str
    file_size: int
    mime_type: str
    resolution: str
    created_at: datetime
    metadata: Dict[str, Any] = {}


class DesignServiceClient:
    """Client for interacting with Design Service."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 120.0,  # Longer timeout for rendering operations
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        """Initialize Design Service client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Initialize circuit breaker
        if circuit_breaker_config is None:
            circuit_breaker_config = CircuitBreakerConfig(
                failure_threshold=5, recovery_timeout=60, success_threshold=3
            )
        self.circuit_breaker = CircuitBreaker("design-service", circuit_breaker_config)

        # Initialize retry config with exponential backoff
        if retry_config is None:
            retry_config = RetryConfig(
                max_attempts=5,  # More attempts for rendering
                base_delay=1.0,
                max_delay=16.0,  # Max 16 seconds
                exponential_base=2.0,
                retryable_exceptions=[httpx.TimeoutException, httpx.ConnectError],
                retryable_status_codes=[502, 503, 504],
            )
        self.retry_config = retry_config

        # HTTP client
        self._client = httpx.AsyncClient(timeout=timeout)

        logger.info(f"DesignServiceClient initialized with base_url={base_url}")

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def _make_request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make HTTP request with circuit breaker and retry logic."""
        url = f"{self.base_url}{path}"

        async def _request():
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        # Execute with circuit breaker and retry
        return await self.circuit_breaker.call_async(
            retry_async_call, _request, config=self.retry_config
        )

    async def request_rendering(
        self, design_id: UUID, render_type: RenderType, parameters: RenderParameters
    ) -> RenderJob:
        """
        Request visual rendering from Design Service.

        Args:
            design_id: Design document ID
            render_type: Type of rendering to generate
            parameters: Rendering parameters

        Returns:
            RenderJob with job information

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        try:
            request_data = {
                "design_id": str(design_id),
                "render_type": render_type.value,
                **parameters.model_dump(exclude={"render_type"}, exclude_none=True),
            }

            response = await self._make_request(
                "POST", "/api/v1/render/jobs", json=request_data
            )

            data = response.json()
            job = RenderJob(**data)

            logger.info(
                f"Rendering job created: job_id={job.job_id}, "
                f"design_id={design_id}, render_type={render_type}"
            )

            return job

        except Exception as e:
            logger.error(
                f"Failed to request rendering for design {design_id}, "
                f"render_type={render_type}: {e}"
            )
            raise

    async def get_render_status(self, job_id: UUID) -> RenderJob:
        """
        Check rendering job status.

        Args:
            job_id: Rendering job ID

        Returns:
            RenderJob with current status

        Raises:
            httpx.HTTPStatusError: If job not found or request fails
        """
        try:
            response = await self._make_request("GET", f"/api/v1/render/jobs/{job_id}")

            data = response.json()
            job = RenderJob(**data)

            logger.debug(f"Render job status: job_id={job_id}, status={job.status}")

            return job

        except Exception as e:
            logger.error(f"Failed to get render status for job {job_id}: {e}")
            raise

    async def retrieve_outputs(self, job_id: UUID) -> List[VisualOutput]:
        """
        Retrieve completed visual outputs.

        Args:
            job_id: Rendering job ID

        Returns:
            List of visual outputs

        Raises:
            httpx.HTTPStatusError: If job not found or not completed
        """
        try:
            response = await self._make_request(
                "GET", f"/api/v1/render/jobs/{job_id}/outputs"
            )

            data = response.json()
            outputs = [VisualOutput(**item) for item in data.get("outputs", [])]

            logger.info(f"Retrieved {len(outputs)} visual outputs for job {job_id}")

            return outputs

        except Exception as e:
            logger.error(f"Failed to retrieve outputs for job {job_id}: {e}")
            raise
