"""Request routing and load balancing implementation."""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse

from ..core.config import get_settings
from ..core.exceptions import ServiceUnavailableError, ValidationError
from ..models.service import ServiceEndpoint, ServiceRoute
from .service_registry import ServiceRegistry

logger = logging.getLogger(__name__)


class RequestRouter:
    """Handles request routing and load balancing to microservices."""

    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self.settings = get_settings()
        self._route_patterns: List[ServiceRoute] = []
        self._load_balancer = RoundRobinLoadBalancer()
        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0), follow_redirects=False
        )
        await self._initialize_routes()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._http_client:
            await self._http_client.aclose()

    async def _initialize_routes(self):
        """Initialize default service routes."""
        default_routes = [
            ServiceRoute(
                path_pattern=r"^/api/v1/users(/.*)?$",
                service_name="user-service",
                strip_prefix=False,
                timeout_seconds=30,
                retry_attempts=3,
            ),
            ServiceRoute(
                path_pattern=r"^/api/v1/projects(/.*)?$",
                service_name="project-service",
                strip_prefix=False,
                timeout_seconds=30,
                retry_attempts=3,
            ),
            ServiceRoute(
                path_pattern=r"^/api/v1/designs(/.*)?$",
                service_name="design-service",
                strip_prefix=False,
                timeout_seconds=60,  # Longer timeout for design operations
                retry_attempts=2,
            ),
            ServiceRoute(
                path_pattern=r"^/api/v1/knowledge(/.*)?$",
                service_name="knowledge-service",
                strip_prefix=False,
                timeout_seconds=45,
                retry_attempts=3,
            ),
            ServiceRoute(
                path_pattern=r"^/api/v1/marketplace(/.*)?$",
                service_name="marketplace-service",
                strip_prefix=False,
                timeout_seconds=30,
                retry_attempts=3,
            ),
            ServiceRoute(
                path_pattern=r"^/api/v1/analytics(/.*)?$",
                service_name="analytics-service",
                strip_prefix=False,
                timeout_seconds=30,
                retry_attempts=3,
            ),
        ]
        self._route_patterns = default_routes
        logger.info(f"Initialized {len(default_routes)} default routes")

    def add_route(self, route: ServiceRoute):
        """Add a new route pattern."""
        self._route_patterns.append(route)
        logger.info(f"Added route: {route.path_pattern} -> {route.service_name}")

    def remove_route(self, path_pattern: str):
        """Remove a route pattern."""
        self._route_patterns = [
            route
            for route in self._route_patterns
            if route.path_pattern != path_pattern
        ]
        logger.info(f"Removed route: {path_pattern}")

    async def route_request(self, request: Request) -> Response:
        """
        Route an incoming request to the appropriate service.

        Args:
            request: The incoming FastAPI request

        Returns:
            Response from the target service

        Raises:
            ServiceUnavailableError: If no service can handle the request
            ValidationError: If the request is invalid
        """
        # Find matching route
        route = self._find_matching_route(request.url.path)
        if not route:
            raise ServiceUnavailableError(
                "unknown", {"reason": f"No route found for path: {request.url.path}"}
            )

        # Get healthy endpoint for the service
        endpoint = await self._load_balancer.get_endpoint(
            self.service_registry, route.service_name
        )

        # Forward the request
        return await self._forward_request(request, endpoint, route)

    def _find_matching_route(self, path: str) -> Optional[ServiceRoute]:
        """Find the first route that matches the given path."""
        for route in self._route_patterns:
            if re.match(route.path_pattern, path):
                return route
        return None

    async def _forward_request(
        self, request: Request, endpoint: ServiceEndpoint, route: ServiceRoute
    ) -> Response:
        """Forward the request to the target service."""
        if not self._http_client:
            raise ServiceUnavailableError(
                route.service_name, {"reason": "HTTP client not initialized"}
            )

        # Prepare target URL
        target_path = request.url.path
        if route.strip_prefix:
            # Remove the matched prefix (implementation depends on requirements)
            target_path = target_path

        target_url = f"{endpoint.url}{target_path}"
        if request.url.query:
            target_url += f"?{request.url.query}"

        # Prepare headers
        headers = dict(request.headers)
        # Remove hop-by-hop headers
        hop_by_hop_headers = {
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "upgrade",
            "host",
        }
        headers = {
            k: v for k, v in headers.items() if k.lower() not in hop_by_hop_headers
        }

        # Add forwarding headers
        headers["X-Forwarded-For"] = (
            request.client.host if request.client else "unknown"
        )
        headers["X-Forwarded-Proto"] = request.url.scheme
        headers["X-Forwarded-Host"] = request.headers.get("host", "unknown")

        # Get request body
        body = await request.body()

        try:
            # Make the request with retry logic
            response = await self._make_request_with_retry(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None,
                timeout=route.timeout_seconds,
                max_retries=route.retry_attempts,
            )

            # Prepare response headers
            response_headers = dict(response.headers)
            # Remove hop-by-hop headers from response
            response_headers = {
                k: v
                for k, v in response_headers.items()
                if k.lower() not in hop_by_hop_headers
            }

            # Return streaming response for large responses
            if int(response.headers.get("content-length", 0)) > 1024 * 1024:  # 1MB
                return StreamingResponse(
                    response.aiter_bytes(),
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get("content-type"),
                )
            else:
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get("content-type"),
                )

        except httpx.TimeoutException:
            raise ServiceUnavailableError(
                route.service_name,
                {"reason": "Request timeout", "timeout_seconds": route.timeout_seconds},
            )
        except httpx.ConnectError:
            raise ServiceUnavailableError(
                route.service_name,
                {"reason": "Connection failed", "endpoint": endpoint.url},
            )
        except Exception as e:
            logger.error(f"Error forwarding request to {endpoint.url}: {e}")
            raise ServiceUnavailableError(
                route.service_name, {"reason": f"Request forwarding failed: {str(e)}"}
            )

    async def _make_request_with_retry(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        content: Optional[bytes],
        timeout: int,
        max_retries: int,
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                response = await self._http_client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=content,
                    timeout=timeout,
                )

                # Don't retry on client errors (4xx) or success (2xx, 3xx)
                if response.status_code < 500:
                    return response

                # Retry on server errors (5xx)
                if attempt < max_retries:
                    logger.warning(
                        f"Request failed with {response.status_code}, "
                        f"retrying ({attempt + 1}/{max_retries}): {url}"
                    )
                    continue
                else:
                    return response

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e
                if attempt < max_retries:
                    logger.warning(
                        f"Request failed with {type(e).__name__}, "
                        f"retrying ({attempt + 1}/{max_retries}): {url}"
                    )
                    continue
                else:
                    raise

        # This should not be reached, but just in case
        if last_exception:
            raise last_exception
        raise Exception("Unexpected error in retry logic")

    def get_routes(self) -> List[ServiceRoute]:
        """Get all configured routes."""
        return self._route_patterns.copy()


class RoundRobinLoadBalancer:
    """Simple round-robin load balancer."""

    def __init__(self):
        self._counters: Dict[str, int] = {}

    async def get_endpoint(
        self, service_registry: ServiceRegistry, service_name: str
    ) -> ServiceEndpoint:
        """
        Get the next endpoint using round-robin algorithm.

        Args:
            service_registry: Service registry instance
            service_name: Name of the service

        Returns:
            Selected service endpoint

        Raises:
            ServiceUnavailableError: If no healthy endpoints are available
        """
        endpoints = await service_registry.discover_services(service_name)

        if not endpoints:
            raise ServiceUnavailableError(
                service_name, {"reason": "No registered endpoints"}
            )

        # Filter healthy endpoints
        healthy_endpoints = [
            ep for ep in endpoints if ep.health_status.value == "healthy"
        ]

        if not healthy_endpoints:
            # If no healthy endpoints, try unknown status endpoints
            unknown_endpoints = [
                ep for ep in endpoints if ep.health_status.value == "unknown"
            ]
            if unknown_endpoints:
                healthy_endpoints = unknown_endpoints
            else:
                raise ServiceUnavailableError(
                    service_name, {"reason": "No healthy endpoints available"}
                )

        # Round-robin selection
        if service_name not in self._counters:
            self._counters[service_name] = 0

        selected_index = self._counters[service_name] % len(healthy_endpoints)
        self._counters[service_name] += 1

        selected_endpoint = healthy_endpoints[selected_index]

        logger.debug(
            f"Selected endpoint {selected_index + 1}/{len(healthy_endpoints)} "
            f"for {service_name}: {selected_endpoint.url}"
        )

        return selected_endpoint
