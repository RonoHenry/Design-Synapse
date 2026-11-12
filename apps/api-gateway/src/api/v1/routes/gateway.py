"""Main gateway routing endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from ....core.exceptions import GatewayError
from ....services.request_router import RequestRouter
from ....services.service_registry import ServiceRegistry, get_service_registry

logger = logging.getLogger(__name__)

router = APIRouter()

# Global router instance
_request_router: RequestRouter = None


async def get_request_router(
    service_registry: ServiceRegistry = Depends(get_service_registry),
) -> RequestRouter:
    """Get the global request router instance."""
    global _request_router
    if _request_router is None:
        _request_router = RequestRouter(service_registry)
        await _request_router.__aenter__()
    return _request_router


@router.api_route(
    "/api/v1/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    include_in_schema=False,
)
async def route_request(
    request: Request,
    path: str,
    request_router: RequestRouter = Depends(get_request_router),
) -> Response:
    """
    Main gateway endpoint that routes requests to appropriate services.

    This endpoint catches all requests to /api/v1/* and forwards them
    to the appropriate microservice based on the configured routing rules.
    """
    try:
        # Add request ID for tracing
        if not hasattr(request.state, "request_id"):
            import uuid

            request.state.request_id = str(uuid.uuid4())

        logger.info(
            f"Routing request: {request.method} {request.url.path} "
            f"[{request.state.request_id}]"
        )

        # Route the request
        response = await request_router.route_request(request)

        logger.info(
            f"Request completed: {request.method} {request.url.path} "
            f"-> {response.status_code} [{request.state.request_id}]"
        )

        return response

    except GatewayError:
        # Re-raise gateway errors to be handled by global exception handler
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error routing request {request.method} {request.url.path}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/routes")
async def get_routes(request_router: RequestRouter = Depends(get_request_router)):
    """
    Get all configured routes.

    Returns the current routing configuration for debugging and monitoring.
    """
    routes = request_router.get_routes()
    return {
        "routes": [
            {
                "path_pattern": route.path_pattern,
                "service_name": route.service_name,
                "strip_prefix": route.strip_prefix,
                "timeout_seconds": route.timeout_seconds,
                "retry_attempts": route.retry_attempts,
            }
            for route in routes
        ],
        "total_routes": len(routes),
    }


@router.post("/routes")
async def add_route(
    route_data: dict, request_router: RequestRouter = Depends(get_request_router)
):
    """
    Add a new route configuration.

    This endpoint allows dynamic addition of new routing rules.
    """
    try:
        from ....models.service import ServiceRoute

        route = ServiceRoute(**route_data)
        request_router.add_route(route)

        return {
            "message": "Route added successfully",
            "route": {
                "path_pattern": route.path_pattern,
                "service_name": route.service_name,
                "strip_prefix": route.strip_prefix,
                "timeout_seconds": route.timeout_seconds,
                "retry_attempts": route.retry_attempts,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid route configuration: {str(e)}"
        )


@router.delete("/routes/{path_pattern:path}")
async def remove_route(
    path_pattern: str, request_router: RequestRouter = Depends(get_request_router)
):
    """
    Remove a route configuration.

    This endpoint allows dynamic removal of routing rules.
    """
    # URL decode the path pattern
    import urllib.parse

    decoded_pattern = urllib.parse.unquote(path_pattern)

    request_router.remove_route(decoded_pattern)

    return {"message": "Route removed successfully", "path_pattern": decoded_pattern}
