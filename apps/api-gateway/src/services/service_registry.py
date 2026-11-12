"""Service registry implementation."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx

from ..core.config import get_settings
from ..core.exceptions import ServiceUnavailableError
from ..models.service import (HealthStatus, ServiceEndpoint, ServiceInfo,
                              SystemHealthStatus)

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Service registry for managing service discovery and health monitoring."""

    def __init__(self):
        self.settings = get_settings()
        self._services: Dict[str, List[ServiceEndpoint]] = {}
        self._health_check_interval = 30  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._http_client = httpx.AsyncClient(timeout=10.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._http_client:
            await self._http_client.aclose()
        if self._health_check_task:
            self._health_check_task.cancel()

    async def register_service(self, service: ServiceInfo) -> bool:
        """
        Register a service with the registry.

        Args:
            service: Service information to register

        Returns:
            True if registration was successful
        """
        try:
            endpoint = ServiceEndpoint(
                service_name=service.name,
                url=f"http://{service.host}:{service.port}",
                health_status=HealthStatus.UNKNOWN,
                last_health_check=None,
                response_time_ms=None,
            )

            if service.name not in self._services:
                self._services[service.name] = []

            # Remove existing endpoint with same URL if exists
            self._services[service.name] = [
                ep for ep in self._services[service.name] if ep.url != endpoint.url
            ]

            # Add new endpoint
            self._services[service.name].append(endpoint)

            logger.info(f"Registered service: {service.name} at {endpoint.url}")

            # Start health checking if not already running
            if not self._health_check_task:
                self._health_check_task = asyncio.create_task(self._health_check_loop())

            return True

        except Exception as e:
            logger.error(f"Failed to register service {service.name}: {e}")
            return False

    async def deregister_service(
        self, service_name: str, url: Optional[str] = None
    ) -> bool:
        """
        Deregister a service from the registry.

        Args:
            service_name: Name of the service to deregister
            url: Specific URL to deregister (if None, deregisters all instances)

        Returns:
            True if deregistration was successful
        """
        try:
            if service_name not in self._services:
                return False

            if url:
                # Remove specific endpoint
                self._services[service_name] = [
                    ep for ep in self._services[service_name] if ep.url != url
                ]
                if not self._services[service_name]:
                    del self._services[service_name]
            else:
                # Remove all endpoints for the service
                del self._services[service_name]

            logger.info(f"Deregistered service: {service_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to deregister service {service_name}: {e}")
            return False

    async def discover_services(self, service_name: str) -> List[ServiceEndpoint]:
        """
        Discover available endpoints for a service.

        Args:
            service_name: Name of the service to discover

        Returns:
            List of available service endpoints
        """
        return self._services.get(service_name, [])

    async def get_healthy_endpoint(self, service_name: str) -> ServiceEndpoint:
        """
        Get a healthy endpoint for a service using round-robin load balancing.

        Args:
            service_name: Name of the service

        Returns:
            A healthy service endpoint

        Raises:
            ServiceUnavailableError: If no healthy endpoints are available
        """
        endpoints = await self.discover_services(service_name)

        if not endpoints:
            raise ServiceUnavailableError(
                service_name, {"reason": "No registered endpoints"}
            )

        # Filter healthy endpoints
        healthy_endpoints = [
            ep for ep in endpoints if ep.health_status == HealthStatus.HEALTHY
        ]

        if not healthy_endpoints:
            # If no healthy endpoints, try unknown status endpoints
            unknown_endpoints = [
                ep for ep in endpoints if ep.health_status == HealthStatus.UNKNOWN
            ]
            if unknown_endpoints:
                healthy_endpoints = unknown_endpoints
            else:
                raise ServiceUnavailableError(
                    service_name, {"reason": "No healthy endpoints available"}
                )

        # Simple round-robin selection (in production, use more sophisticated algorithm)
        # For now, return the first healthy endpoint
        return healthy_endpoints[0]

    async def get_system_health(self) -> SystemHealthStatus:
        """
        Get overall system health status.

        Returns:
            System health status with service details
        """
        all_endpoints = []
        for endpoints in self._services.values():
            all_endpoints.extend(endpoints)

        healthy_count = sum(
            1 for ep in all_endpoints if ep.health_status == HealthStatus.HEALTHY
        )

        overall_status = HealthStatus.HEALTHY
        if healthy_count == 0 and all_endpoints:
            overall_status = HealthStatus.UNHEALTHY
        elif healthy_count < len(all_endpoints):
            overall_status = HealthStatus.UNKNOWN

        return SystemHealthStatus(
            status=overall_status,
            services=all_endpoints,
            timestamp=datetime.utcnow(),
            total_services=len(all_endpoints),
            healthy_services=healthy_count,
        )

    async def _health_check_loop(self):
        """Background task for periodic health checks."""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)  # Short delay before retrying

    async def _perform_health_checks(self):
        """Perform health checks on all registered services."""
        if not self._http_client:
            return

        tasks = []
        for service_name, endpoints in self._services.items():
            for endpoint in endpoints:
                task = asyncio.create_task(self._check_endpoint_health(endpoint))
                tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_endpoint_health(self, endpoint: ServiceEndpoint):
        """Check health of a specific endpoint."""
        if not self._http_client:
            return

        health_url = f"{endpoint.url}/health"
        start_time = datetime.utcnow()

        try:
            response = await self._http_client.get(health_url)
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            if response.status_code == 200:
                endpoint.health_status = HealthStatus.HEALTHY
                endpoint.response_time_ms = response_time
            else:
                endpoint.health_status = HealthStatus.UNHEALTHY
                endpoint.response_time_ms = None

            endpoint.last_health_check = datetime.utcnow()

        except Exception as e:
            logger.debug(f"Health check failed for {endpoint.url}: {e}")
            endpoint.health_status = HealthStatus.UNHEALTHY
            endpoint.response_time_ms = None
            endpoint.last_health_check = datetime.utcnow()

            # Remove endpoints that have been unhealthy for too long
            if (
                endpoint.last_health_check
                and datetime.utcnow() - endpoint.last_health_check
                > timedelta(minutes=5)
            ):
                await self._remove_unhealthy_endpoint(endpoint)

    async def _remove_unhealthy_endpoint(self, endpoint: ServiceEndpoint):
        """Remove an endpoint that has been unhealthy for too long."""
        for service_name, endpoints in self._services.items():
            if endpoint in endpoints:
                endpoints.remove(endpoint)
                logger.info(f"Removed unhealthy endpoint: {endpoint.url}")
                if not endpoints:
                    del self._services[service_name]
                break


# Global service registry instance
_service_registry: Optional[ServiceRegistry] = None


async def get_service_registry() -> ServiceRegistry:
    """Get the global service registry instance."""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
        await _service_registry.__aenter__()
    return _service_registry
