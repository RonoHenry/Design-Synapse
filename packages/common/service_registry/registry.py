"""Service Registry implementation with health monitoring and service discovery."""

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from .health_checker import HealthChecker
from .models import (HealthCheck, HealthStatus, ServiceDiscoveryFilter,
                     ServiceEndpoint, ServiceInfo, ServiceRegistrationRequest,
                     SystemHealthStatus)

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Service registry for managing service discovery and health monitoring."""

    def __init__(
        self,
        default_health_check_interval: int = 30,
        default_failure_threshold: int = 3,
        cleanup_interval: int = 300,  # 5 minutes
        stale_service_timeout: int = 600,  # 10 minutes
    ):
        """
        Initialize service registry.

        Args:
            default_health_check_interval: Default health check interval in seconds
            default_failure_threshold: Default failure threshold before marking unhealthy
            cleanup_interval: Interval for cleaning up stale services in seconds
            stale_service_timeout: Timeout for considering services stale in seconds
        """
        self.default_health_check_interval = default_health_check_interval
        self.default_failure_threshold = default_failure_threshold
        self.cleanup_interval = cleanup_interval
        self.stale_service_timeout = stale_service_timeout

        # Service storage: service_name -> {instance_id -> ServiceEndpoint}
        self._services: Dict[str, Dict[str, ServiceEndpoint]] = defaultdict(dict)

        # Service configurations: instance_id -> config
        self._service_configs: Dict[str, Dict] = {}

        # Health checker
        self._health_checker: Optional[HealthChecker] = None

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def start(self):
        """Start the service registry and health monitoring."""
        if self._running:
            return

        self._running = True

        # Initialize health checker
        self._health_checker = HealthChecker(
            check_interval=self.default_health_check_interval,
            failure_threshold=self.default_failure_threshold,
        )
        await self._health_checker.__aenter__()

        # Add callback for automatic service deregistration
        self._health_checker.add_health_callback(self._handle_health_change)

        # Start health checking
        await self._health_checker.start()

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("Service registry started")

    async def stop(self):
        """Stop the service registry and cleanup resources."""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._health_checker:
            await self._health_checker.__aexit__(None, None, None)

        logger.info("Service registry stopped")

    async def register_service(self, request: ServiceRegistrationRequest) -> str:
        """
        Register a service with the registry.

        Args:
            request: Service registration request

        Returns:
            Instance ID for the registered service
        """
        service = request.service
        instance_id = str(uuid.uuid4())

        # Create service endpoint
        endpoint = ServiceEndpoint(
            service_name=service.name,
            instance_id=instance_id,
            url=f"http://{service.host}:{service.port}",
            health_status=HealthStatus.UNKNOWN,
            metadata=service.metadata,
            tags=service.tags,
        )

        # Store service
        self._services[service.name][instance_id] = endpoint

        # Store configuration
        self._service_configs[instance_id] = {
            "health_check_interval": request.health_check_interval,
            "failure_threshold": request.failure_threshold,
            "health_check_url": service.health_check_url,
        }

        # Add to health checker
        if self._health_checker:
            await self._health_checker.add_endpoint(
                endpoint,
                check_interval=request.health_check_interval,
                failure_threshold=request.failure_threshold,
            )

        logger.info(
            f"Registered service: {service.name} (instance: {instance_id}) at {endpoint.url}"
        )
        return instance_id

    async def deregister_service(
        self, service_name: str, instance_id: Optional[str] = None
    ) -> bool:
        """
        Deregister a service from the registry.

        Args:
            service_name: Name of the service to deregister
            instance_id: Specific instance ID to deregister (if None, deregisters all instances)

        Returns:
            True if deregistration was successful
        """
        try:
            if service_name not in self._services:
                return False

            if instance_id:
                # Remove specific instance
                if instance_id in self._services[service_name]:
                    del self._services[service_name][instance_id]

                    # Remove from health checker
                    if self._health_checker:
                        await self._health_checker.remove_endpoint(
                            service_name, instance_id
                        )

                    # Remove configuration
                    if instance_id in self._service_configs:
                        del self._service_configs[instance_id]

                    # Remove service entry if no instances left
                    if not self._services[service_name]:
                        del self._services[service_name]

                    logger.info(
                        f"Deregistered service instance: {service_name}:{instance_id}"
                    )
                else:
                    return False
            else:
                # Remove all instances
                for inst_id in list(self._services[service_name].keys()):
                    if self._health_checker:
                        await self._health_checker.remove_endpoint(
                            service_name, inst_id
                        )
                    if inst_id in self._service_configs:
                        del self._service_configs[inst_id]

                del self._services[service_name]
                logger.info(f"Deregistered all instances of service: {service_name}")

            return True

        except Exception as e:
            logger.error(f"Failed to deregister service {service_name}: {e}")
            return False

    async def discover_services(
        self, filter_criteria: Optional[ServiceDiscoveryFilter] = None
    ) -> List[ServiceEndpoint]:
        """
        Discover services based on filter criteria.

        Args:
            filter_criteria: Optional filter criteria

        Returns:
            List of matching service endpoints
        """
        all_endpoints = []

        # Collect all endpoints
        for service_instances in self._services.values():
            all_endpoints.extend(service_instances.values())

        # Apply filters if provided
        if filter_criteria:
            filtered_endpoints = []

            for endpoint in all_endpoints:
                # Filter by service name
                if (
                    filter_criteria.service_name
                    and endpoint.service_name != filter_criteria.service_name
                ):
                    continue

                # Filter by health status
                if (
                    filter_criteria.health_status
                    and endpoint.health_status != filter_criteria.health_status
                ):
                    continue

                # Filter by tags (all must match)
                if filter_criteria.tags:
                    if not all(tag in endpoint.tags for tag in filter_criteria.tags):
                        continue

                # Filter by response time
                if endpoint.response_time_ms is not None:
                    if (
                        filter_criteria.min_response_time
                        and endpoint.response_time_ms
                        < filter_criteria.min_response_time
                    ):
                        continue
                    if (
                        filter_criteria.max_response_time
                        and endpoint.response_time_ms
                        > filter_criteria.max_response_time
                    ):
                        continue

                filtered_endpoints.append(endpoint)

            return filtered_endpoints

        return all_endpoints

    async def get_healthy_endpoint(
        self, service_name: str
    ) -> Optional[ServiceEndpoint]:
        """
        Get a healthy endpoint for a service using round-robin load balancing.

        Args:
            service_name: Name of the service

        Returns:
            A healthy service endpoint or None if no healthy endpoints available
        """
        if service_name not in self._services:
            return None

        endpoints = list(self._services[service_name].values())

        # Filter healthy endpoints
        healthy_endpoints = [
            ep for ep in endpoints if ep.health_status == HealthStatus.HEALTHY
        ]

        if healthy_endpoints:
            # Simple round-robin (in production, use more sophisticated algorithm)
            # Sort by response time for now
            healthy_endpoints.sort(key=lambda x: x.response_time_ms or float("inf"))
            return healthy_endpoints[0]

        # If no healthy endpoints, try unknown status endpoints
        unknown_endpoints = [
            ep for ep in endpoints if ep.health_status == HealthStatus.UNKNOWN
        ]

        if unknown_endpoints:
            return unknown_endpoints[0]

        return None

    async def get_system_health(self) -> SystemHealthStatus:
        """
        Get overall system health status.

        Returns:
            System health status with service details
        """
        all_endpoints = []
        for service_instances in self._services.values():
            all_endpoints.extend(service_instances.values())

        # Count services by status
        healthy_count = sum(
            1 for ep in all_endpoints if ep.health_status == HealthStatus.HEALTHY
        )
        unhealthy_count = sum(
            1 for ep in all_endpoints if ep.health_status == HealthStatus.UNHEALTHY
        )
        unknown_count = sum(
            1 for ep in all_endpoints if ep.health_status == HealthStatus.UNKNOWN
        )

        # Determine overall status
        if not all_endpoints:
            overall_status = HealthStatus.UNKNOWN
        elif unhealthy_count == 0:
            overall_status = HealthStatus.HEALTHY
        elif healthy_count == 0:
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN  # Mixed status

        return SystemHealthStatus(
            status=overall_status,
            services=all_endpoints,
            timestamp=datetime.utcnow(),
            total_services=len(all_endpoints),
            healthy_services=healthy_count,
            unhealthy_services=unhealthy_count,
            unknown_services=unknown_count,
        )

    async def get_service_instances(self, service_name: str) -> List[ServiceEndpoint]:
        """
        Get all instances of a specific service.

        Args:
            service_name: Name of the service

        Returns:
            List of service instances
        """
        if service_name not in self._services:
            return []

        return list(self._services[service_name].values())

    async def get_all_services(self) -> Dict[str, List[ServiceEndpoint]]:
        """
        Get all registered services.

        Returns:
            Dictionary mapping service names to their instances
        """
        result = {}
        for service_name, instances in self._services.items():
            result[service_name] = list(instances.values())
        return result

    def _handle_health_change(
        self, endpoint: ServiceEndpoint, health_check: HealthCheck
    ):
        """
        Handle health status changes from the health checker.

        Args:
            endpoint: Service endpoint that changed
            health_check: Health check result
        """
        # Log significant health changes
        if health_check.status == HealthStatus.UNHEALTHY:
            logger.warning(
                f"Service became unhealthy: {endpoint.service_name}:{endpoint.instance_id}"
            )
        elif health_check.status == HealthStatus.HEALTHY:
            logger.info(
                f"Service became healthy: {endpoint.service_name}:{endpoint.instance_id}"
            )

        # Automatic deregistration could be implemented here
        # For now, we just log the change

    async def _cleanup_loop(self):
        """Background task for cleaning up stale services."""
        while self._running:
            try:
                await self._cleanup_stale_services()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying

    async def _cleanup_stale_services(self):
        """Remove services that haven't been seen for a long time."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.stale_service_timeout)

        services_to_remove = []

        for service_name, instances in self._services.items():
            for instance_id, endpoint in instances.items():
                # Check if service is stale (no recent health checks and unhealthy)
                if (
                    endpoint.health_status == HealthStatus.UNHEALTHY
                    and endpoint.last_health_check
                    and endpoint.last_health_check < cutoff_time
                ):
                    services_to_remove.append((service_name, instance_id))

        # Remove stale services
        for service_name, instance_id in services_to_remove:
            await self.deregister_service(service_name, instance_id)
            logger.info(f"Cleaned up stale service: {service_name}:{instance_id}")


# Global service registry instance
_service_registry: Optional[ServiceRegistry] = None


async def get_service_registry() -> ServiceRegistry:
    """Get the global service registry instance."""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
        await _service_registry.start()
    return _service_registry
