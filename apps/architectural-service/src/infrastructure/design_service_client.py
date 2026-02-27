"""
Design Service client for visual rendering and generation.
"""

import hashlib
import json
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

# Try to import cache, but make it optional for testing
try:
    from ..core.cache import get_cache

    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

    def get_cache():
        return None


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

        # Get Redis cache instance if available
        self.cache = get_cache() if CACHE_AVAILABLE else None

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

    def _generate_design_hash(
        self, design_id: UUID, design_version: str, parameters: RenderParameters
    ) -> str:
        """Generate hash for design and parameters to use as cache key."""
        cache_data = {
            "design_id": str(design_id),
            "design_version": design_version,
            "parameters": parameters.model_dump(),
        }
        cache_json = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_json.encode()).hexdigest()

    async def invalidate_rendering_cache(self, design_id: Optional[UUID] = None):
        """Invalidate rendering cache entries."""
        if self.cache:
            return await self.cache.invalidate_rendering_cache(
                str(design_id) if design_id else None
            )
        return 0

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

    async def get_cached_outputs(
        self, design_id: UUID, design_version: str, parameters: RenderParameters
    ) -> Optional[List[VisualOutput]]:
        """
        Check if rendered outputs are cached for given design and parameters.

        Args:
            design_id: Design document ID
            design_version: Design version
            parameters: Rendering parameters

        Returns:
            Cached visual outputs if available, None otherwise
        """
        if not self.cache:
            return None

        design_hash = self._generate_design_hash(design_id, design_version, parameters)
        cache_key = f"rendering:{design_id}:{design_hash}"

        result = await self.cache.cache_manager.get(cache_key)
        if result.value is not None:
            logger.info(f"Found cached rendering outputs for design {design_id}")
            return [VisualOutput(**item) for item in result.value]

        return None

    async def cache_outputs(
        self,
        design_id: UUID,
        design_version: str,
        parameters: RenderParameters,
        outputs: List[VisualOutput],
    ):
        """
        Cache rendered outputs for reuse.

        Args:
            design_id: Design document ID
            design_version: Design version
            parameters: Rendering parameters
            outputs: Visual outputs to cache
        """
        if not self.cache:
            return

        design_hash = self._generate_design_hash(design_id, design_version, parameters)
        cache_key = f"rendering:{design_id}:{design_hash}"

        # Cache for 24 hours (86400 seconds) since renderings are expensive
        cache_data = [output.model_dump() for output in outputs]
        await self.cache.cache_manager.set(cache_key, cache_data, ttl=86400)

        logger.info(f"Cached {len(outputs)} rendering outputs for design {design_id}")

    async def request_rendering_with_cache(
        self,
        design_id: UUID,
        design_version: str,
        render_type: RenderType,
        parameters: RenderParameters,
    ) -> tuple[RenderJob, Optional[List[VisualOutput]]]:
        """
        Request rendering with cache check.

        Args:
            design_id: Design document ID
            design_version: Design version
            render_type: Type of rendering to generate
            parameters: Rendering parameters

        Returns:
            Tuple of (RenderJob, cached_outputs if available)
        """
        # Check cache first
        cached_outputs = await self.get_cached_outputs(
            design_id, design_version, parameters
        )
        if cached_outputs:
            # Create a mock job for cached results
            mock_job = RenderJob(
                job_id=UUID("00000000-0000-0000-0000-000000000000"),
                design_id=design_id,
                render_type=render_type,
                status=RenderStatus.COMPLETED,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            )
            return mock_job, cached_outputs

        # No cache hit, request new rendering
        job = await self.request_rendering(design_id, render_type, parameters)
        return job, None
