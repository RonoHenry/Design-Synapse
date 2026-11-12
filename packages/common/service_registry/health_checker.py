"""Health checker for monitoring service health."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

import httpx

from .models import HealthCheck, HealthStatus, ServiceEndpoint

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health checker for monitoring service endpoints."""

    def __init__(
        self,
        check_interval: int = 30,
        timeout: float = 10.0,
        failure_threshold: int = 3,
        recovery_threshold: int = 2,
    ):
        """
        Initialize health checker.

        Args:
            check_interval: Interval between health checks in seconds
            timeout: HTTP request timeout in seconds
            failure_threshold: Number of consecutive failures before marking unhealthy
            recovery_threshold: Number of consecutive successes needed for recovery
        """
        self.check_interval = check_interval
        self.timeout = timeout
        self.failure_threshold = failure_threshold
        self.recovery_threshold = recovery_threshold

        self._http_client: Optional[httpx.AsyncClient] = None
        self._check_task: Optional[asyncio.Task] = None
        self._endpoints: Dict[str, ServiceEndpoint] = {}
        self._endpoint_configs: Dict[str, Dict] = {}
        self._running = False
        self._callbacks: List[Callable[[ServiceEndpoint, HealthCheck], None]] = []

    async def __aenter__(self):
        """Async context manager entry."""
        self._http_client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
        if self._http_client:
            await self._http_client.aclose()

    def add_health_callback(
        self, callback: Callable[[ServiceEndpoint, HealthCheck], None]
    ):
        """
        Add a callback to be called when health status changes.

        Args:
            callback: Function to call with (endpoint, health_check) parameters
        """
        self._callbacks.append(callback)

    def remove_health_callback(
        self, callback: Callable[[ServiceEndpoint, HealthCheck], None]
    ):
        """
        Remove a health callback.

        Args:
            callback: Callback function to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def add_endpoint(
        self,
        endpoint: ServiceEndpoint,
        check_interval: Optional[int] = None,
        failure_threshold: Optional[int] = None,
    ):
        """
        Add an endpoint for health monitoring.

        Args:
            endpoint: Service endpoint to monitor
            check_interval: Override default check interval
            failure_threshold: Override default failure threshold
        """
        endpoint_id = f"{endpoint.service_name}:{endpoint.instance_id}"
        self._endpoints[endpoint_id] = endpoint
        self._endpoint_configs[endpoint_id] = {
            "check_interval": check_interval or self.check_interval,
            "failure_threshold": failure_threshold or self.failure_threshold,
            "last_check": None,
            "consecutive_successes": 0,
        }

        logger.info(f"Added endpoint for health monitoring: {endpoint.url}")

    async def remove_endpoint(self, service_name: str, instance_id: str):
        """
        Remove an endpoint from health monitoring.

        Args:
            service_name: Service name
            instance_id: Instance identifier
        """
        endpoint_id = f"{service_name}:{instance_id}"
        if endpoint_id in self._endpoints:
            del self._endpoints[endpoint_id]
            del self._endpoint_configs[endpoint_id]
            logger.info(
                f"Removed endpoint from health monitoring: {service_name}:{instance_id}"
            )

    async def start(self):
        """Start the health checking background task."""
        if self._running:
            return

        self._running = True
        self._check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Health checker started")

    async def stop(self):
        """Stop the health checking background task."""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("Health checker stopped")

    async def check_endpoint_health(self, endpoint: ServiceEndpoint) -> HealthCheck:
        """
        Perform a single health check on an endpoint.

        Args:
            endpoint: Service endpoint to check

        Returns:
            Health check result
        """
        if not self._http_client:
            raise RuntimeError("Health checker not initialized")

        health_url = f"{endpoint.url.rstrip('/')}/health"
        start_time = datetime.utcnow()

        try:
            response = await self._http_client.get(health_url)
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            if response.status_code == 200:
                # Try to parse response for detailed health info
                try:
                    health_data = response.json()
                    message = health_data.get("message", "Service is healthy")
                except:
                    message = "Service is healthy"

                return HealthCheck(
                    name=f"{endpoint.service_name}_health",
                    status=HealthStatus.HEALTHY,
                    message=message,
                    response_time_ms=response_time,
                )
            else:
                return HealthCheck(
                    name=f"{endpoint.service_name}_health",
                    status=HealthStatus.UNHEALTHY,
                    message=f"HTTP {response.status_code}: {response.text[:100]}",
                    response_time_ms=response_time,
                )

        except asyncio.TimeoutError:
            return HealthCheck(
                name=f"{endpoint.service_name}_health",
                status=HealthStatus.UNHEALTHY,
                message="Health check timeout",
                response_time_ms=None,
            )
        except Exception as e:
            return HealthCheck(
                name=f"{endpoint.service_name}_health",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)[:100]}",
                response_time_ms=None,
            )

    async def get_aggregated_health(self) -> List[HealthCheck]:
        """
        Get aggregated health status for all monitored endpoints.

        Returns:
            List of health check results
        """
        health_checks = []

        for endpoint in self._endpoints.values():
            if endpoint.last_health_check:
                # Create health check from last known status
                health_checks.append(
                    HealthCheck(
                        name=f"{endpoint.service_name}_health",
                        status=endpoint.health_status,
                        message=f"Last check: {endpoint.last_health_check.isoformat()}",
                        timestamp=endpoint.last_health_check,
                        response_time_ms=endpoint.response_time_ms,
                    )
                )
            else:
                health_checks.append(
                    HealthCheck(
                        name=f"{endpoint.service_name}_health",
                        status=HealthStatus.UNKNOWN,
                        message="No health checks performed yet",
                    )
                )

        return health_checks

    async def _health_check_loop(self):
        """Background task for periodic health checks."""
        while self._running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)  # Short delay before retrying

    async def _perform_health_checks(self):
        """Perform health checks on all registered endpoints."""
        if not self._endpoints:
            return

        # Create tasks for all health checks
        tasks = []
        for endpoint_id, endpoint in self._endpoints.items():
            config = self._endpoint_configs[endpoint_id]

            # Check if it's time for a health check
            if config["last_check"] is None or datetime.utcnow() - config[
                "last_check"
            ] >= timedelta(seconds=config["check_interval"]):
                task = asyncio.create_task(
                    self._check_and_update_endpoint(endpoint_id, endpoint, config)
                )
                tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_and_update_endpoint(
        self, endpoint_id: str, endpoint: ServiceEndpoint, config: Dict
    ):
        """Check and update a single endpoint's health status."""
        try:
            health_check = await self.check_endpoint_health(endpoint)
            config["last_check"] = datetime.utcnow()

            # Update endpoint health information
            endpoint.last_health_check = health_check.timestamp
            endpoint.response_time_ms = health_check.response_time_ms

            # Handle status transitions
            previous_status = endpoint.health_status

            if health_check.status == HealthStatus.HEALTHY:
                config["consecutive_successes"] += 1
                endpoint.consecutive_failures = 0

                # Mark as healthy if we have enough consecutive successes
                if (
                    previous_status != HealthStatus.HEALTHY
                    and config["consecutive_successes"] >= self.recovery_threshold
                ):
                    endpoint.health_status = HealthStatus.HEALTHY
                    logger.info(f"Endpoint recovered: {endpoint.url}")
                elif previous_status == HealthStatus.UNKNOWN:
                    endpoint.health_status = HealthStatus.HEALTHY

            else:  # UNHEALTHY
                config["consecutive_successes"] = 0
                endpoint.consecutive_failures += 1

                # Mark as unhealthy if we have enough consecutive failures
                if endpoint.consecutive_failures >= config["failure_threshold"]:
                    if endpoint.health_status != HealthStatus.UNHEALTHY:
                        endpoint.health_status = HealthStatus.UNHEALTHY
                        logger.warning(f"Endpoint marked unhealthy: {endpoint.url}")

            # Notify callbacks if status changed
            if previous_status != endpoint.health_status:
                for callback in self._callbacks:
                    try:
                        callback(endpoint, health_check)
                    except Exception as e:
                        logger.error(f"Error in health callback: {e}")

        except Exception as e:
            logger.error(f"Error checking endpoint {endpoint.url}: {e}")
            endpoint.consecutive_failures += 1
            if endpoint.consecutive_failures >= config["failure_threshold"]:
                endpoint.health_status = HealthStatus.UNHEALTHY
