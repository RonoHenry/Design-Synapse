"""
Vendor Service client for material specifications and supplier information.
"""

import logging
import sys
from datetime import datetime
from decimal import Decimal
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


class MaterialQuery(BaseModel):
    """Material search query."""

    query: str
    category: Optional[str] = None
    material_type: Optional[str] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    in_stock: Optional[bool] = None


class VendorMaterial(BaseModel):
    """Material from vendor catalog."""

    material_id: UUID
    name: str
    category: str
    material_type: str
    description: Optional[str] = None
    properties: Dict[str, Any] = {}
    vendor_id: UUID
    vendor_name: str
    price: Decimal
    unit: str
    in_stock: bool
    lead_time_days: Optional[int] = None


class SupplierInfo(BaseModel):
    """Supplier information."""

    vendor_id: UUID
    vendor_name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    rating: Optional[float] = None
    certifications: List[str] = []
    delivery_areas: List[str] = []


class AvailabilityInfo(BaseModel):
    """Material availability information."""

    material_id: UUID
    in_stock: bool
    quantity_available: Optional[int] = None
    lead_time_days: Optional[int] = None
    estimated_delivery: Optional[datetime] = None
    price: Decimal
    minimum_order_quantity: Optional[int] = None


class VendorServiceClient:
    """Client for interacting with Vendor Service."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        """Initialize Vendor Service client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Initialize circuit breaker
        if circuit_breaker_config is None:
            circuit_breaker_config = CircuitBreakerConfig(
                failure_threshold=5, recovery_timeout=60, success_threshold=3
            )
        self.circuit_breaker = CircuitBreaker("vendor-service", circuit_breaker_config)

        # Initialize retry config
        if retry_config is None:
            retry_config = RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=10.0,
                exponential_base=2.0,
                retryable_exceptions=[httpx.TimeoutException, httpx.ConnectError],
                retryable_status_codes=[502, 503, 504],
            )
        self.retry_config = retry_config

        # HTTP client
        self._client = httpx.AsyncClient(timeout=timeout)

        logger.info(f"VendorServiceClient initialized with base_url={base_url}")

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

    async def search_materials(self, query: MaterialQuery) -> List[VendorMaterial]:
        """
        Search for materials in vendor catalog.

        Args:
            query: Material search query

        Returns:
            List of matching materials

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        try:
            params = query.model_dump(exclude_none=True)

            response = await self._make_request(
                "GET", "/api/v1/materials/search", params=params
            )

            data = response.json()
            materials = [VendorMaterial(**item) for item in data.get("materials", [])]

            logger.info(
                f"Found {len(materials)} materials matching query: {query.query}"
            )

            return materials

        except Exception as e:
            logger.error(f"Failed to search materials with query '{query.query}': {e}")
            raise

    async def get_supplier_info(self, material_id: UUID) -> SupplierInfo:
        """
        Get supplier information and pricing.

        Args:
            material_id: Material ID

        Returns:
            Supplier information

        Raises:
            httpx.HTTPStatusError: If material not found or request fails
        """
        try:
            response = await self._make_request(
                "GET", f"/api/v1/materials/{material_id}/supplier"
            )

            data = response.json()
            supplier = SupplierInfo(**data)

            logger.debug(f"Retrieved supplier info for material {material_id}")

            return supplier

        except Exception as e:
            logger.error(f"Failed to get supplier info for material {material_id}: {e}")
            raise

    async def check_availability(
        self, material_id: UUID, quantity: Decimal
    ) -> AvailabilityInfo:
        """
        Check material availability.

        Args:
            material_id: Material ID
            quantity: Requested quantity

        Returns:
            Availability information

        Raises:
            httpx.HTTPStatusError: If material not found or request fails
        """
        try:
            response = await self._make_request(
                "GET",
                f"/api/v1/materials/{material_id}/availability",
                params={"quantity": str(quantity)},
            )

            data = response.json()
            availability = AvailabilityInfo(**data)

            logger.debug(
                f"Checked availability for material {material_id}: "
                f"in_stock={availability.in_stock}"
            )

            return availability

        except Exception as e:
            logger.error(
                f"Failed to check availability for material {material_id}: {e}"
            )
            raise
