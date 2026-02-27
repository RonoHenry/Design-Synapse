"""
Health check aggregation for monitoring system-wide health status.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    from packages.common.service_registry.health_checker import HealthChecker
    from packages.common.service_registry.models import (HealthStatus,
                                                         ServiceEndpoint)
except ImportError:
    # Fallback for when running tests or in different contexts
    from ...service_registry.models import ServiceEndpoint, HealthStatus
    from ...service_registry.health_checker import HealthChecker

from packages.common.monitoring.models import ServiceHealth, SystemHealthStatus


class HealthAggregator:
    """Aggregates health status from multiple services."""

    def __init__(self, health_checker: HealthChecker = None):
        self.health_checker = health_checker or HealthChecker()
        self._service_health: Dict[str, ServiceHealth] = {}
        self._health_history: List[SystemHealthStatus] = []
        self._max_history = 1000  # Keep last 1000 health checks

    async def check_service_health(
        self, service_name: str, endpoint: str
    ) -> ServiceHealth:
        """Check health of a single service."""
        try:
            start_time = datetime.utcnow()

            # Create a service endpoint for health checking
            service_endpoint = ServiceEndpoint(
                service_name=service_name,
                url=endpoint,
                health_status=HealthStatus.UNKNOWN,
                last_health_check=start_time,
                response_time_ms=0.0,
            )

            # Perform health check
            health_result = await self.health_checker.check_endpoint_health(
                service_endpoint
            )
            end_time = datetime.utcnow()
            response_time_ms = (end_time - start_time).total_seconds() * 1000

            service_health = ServiceHealth(
                service_name=service_name,
                status=health_result.status,
                message=health_result.message,
                timestamp=end_time,
                response_time_ms=health_result.response_time_ms or response_time_ms,
                metadata={"health_check": health_result.name},
            )

            # Store the health status
            self._service_health[service_name] = service_health
            return service_health

        except Exception as e:
            service_health = ServiceHealth(
                service_name=service_name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time_ms=None,
                metadata={"error": str(e)},
            )

            self._service_health[service_name] = service_health
            return service_health

    async def check_all_services_health(
        self, services: List[Dict[str, str]]
    ) -> SystemHealthStatus:
        """Check health of all registered services.

        Args:
            services: List of service dictionaries with 'name' and 'health_endpoint' keys
        """
        # Check all services concurrently
        health_tasks = [
            self.check_service_health(service["name"], service["health_endpoint"])
            for service in services
        ]

        service_healths = await asyncio.gather(*health_tasks, return_exceptions=True)

        # Handle any exceptions from health checks
        valid_healths = []
        for i, health in enumerate(service_healths):
            if isinstance(health, Exception):
                # Create unhealthy status for failed health check
                service_name = services[i]["name"]
                failed_health = ServiceHealth(
                    service_name=service_name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check exception: {str(health)}",
                    timestamp=datetime.utcnow(),
                    response_time_ms=None,
                    metadata={"exception": str(health)},
                )
                valid_healths.append(failed_health)
            else:
                valid_healths.append(health)

        # Determine overall system health
        overall_status = self._calculate_overall_status(valid_healths)

        system_health = SystemHealthStatus(
            overall_status=overall_status,
            services=valid_healths,
            timestamp=datetime.utcnow(),
        )

        # Store in history
        self._add_to_history(system_health)

        return system_health

    def _calculate_overall_status(
        self, service_healths: List[ServiceHealth]
    ) -> HealthStatus:
        """Calculate overall system health based on individual service health."""
        if not service_healths:
            return HealthStatus.UNKNOWN

        unhealthy_count = sum(
            1 for h in service_healths if h.status == HealthStatus.UNHEALTHY
        )
        unknown_count = sum(
            1 for h in service_healths if h.status == HealthStatus.UNKNOWN
        )

        # If more than 50% of services are unhealthy, system is unhealthy
        if unhealthy_count > len(service_healths) * 0.5:
            return HealthStatus.UNHEALTHY

        # If any critical services are unhealthy, system is unhealthy
        # (This could be enhanced with service criticality configuration)
        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY

        # If there are unknown services but no unhealthy ones
        if unknown_count > 0:
            return HealthStatus.UNKNOWN

        return HealthStatus.HEALTHY

    def _add_to_history(self, system_health: SystemHealthStatus):
        """Add system health status to history with rotation."""
        self._health_history.append(system_health)

        # Rotate history if we exceed max
        if len(self._health_history) > self._max_history:
            self._health_history = self._health_history[-self._max_history :]

    def get_current_health(self) -> Optional[SystemHealthStatus]:
        """Get the most recent system health status."""
        if not self._health_history:
            return None
        return self._health_history[-1]

    def get_service_health(self, service_name: str) -> Optional[ServiceHealth]:
        """Get health status for a specific service."""
        return self._service_health.get(service_name)

    def get_health_history(self, hours: int = 24) -> List[SystemHealthStatus]:
        """Get health history for the last N hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            health for health in self._health_history if health.timestamp >= cutoff_time
        ]

    def get_unhealthy_services(self) -> List[ServiceHealth]:
        """Get list of currently unhealthy services."""
        return [
            health
            for health in self._service_health.values()
            if health.status == HealthStatus.UNHEALTHY
        ]

    def get_health_summary(self) -> Dict[str, int]:
        """Get summary of service health counts."""
        if not self._service_health:
            return {"healthy": 0, "unhealthy": 0, "unknown": 0}

        summary = {"healthy": 0, "unhealthy": 0, "unknown": 0}
        for health in self._service_health.values():
            if health.status == HealthStatus.HEALTHY:
                summary["healthy"] += 1
            elif health.status == HealthStatus.UNHEALTHY:
                summary["unhealthy"] += 1
            else:
                summary["unknown"] += 1

        return summary

    async def create_basic_health_endpoint_response(
        self, services: List[Dict[str, str]]
    ) -> Dict:
        """Create a basic health check response for API endpoints."""
        system_health = await self.check_all_services_health(services)

        return {
            "status": system_health.overall_status.value,
            "timestamp": system_health.timestamp.isoformat(),
            "services": {
                service.service_name: {
                    "status": service.status.value,
                    "message": service.message,
                    "response_time_ms": service.response_time_ms,
                    "last_check": service.timestamp.isoformat(),
                }
                for service in system_health.services
            },
            "summary": {
                "total": len(system_health.services),
                "healthy": system_health.healthy_count,
                "unhealthy": system_health.unhealthy_count,
                "unknown": system_health.unknown_count,
            },
        }


# Global health aggregator instance
_health_aggregator = HealthAggregator()


def get_health_aggregator() -> HealthAggregator:
    """Get the global health aggregator instance."""
    return _health_aggregator
