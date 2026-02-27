"""Health check endpoints."""

import time
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends

from ....core.config import Settings, get_settings
from ....models.request import HealthResponse
from ....services.service_registry import ServiceRegistry

router = APIRouter()

# Track service start time for uptime calculation
_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """
    Basic health check endpoint.

    Returns the current health status of the API Gateway.
    """
    uptime = time.time() - _start_time

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        uptime_seconds=uptime,
        dependencies={},
    )


@router.get("/health/detailed")
async def detailed_health_check(
    settings: Settings = Depends(get_settings),
    service_registry: ServiceRegistry = Depends(),
) -> Dict:
    """
    Detailed health check with service registry status.

    Returns comprehensive health information including registered services.
    """
    uptime = time.time() - _start_time

    # Get system health from service registry
    try:
        system_health = await service_registry.get_system_health()
        dependencies = {
            "service_registry": "healthy",
            "registered_services": system_health.total_services,
            "healthy_services": system_health.healthy_services,
        }
    except Exception as e:
        dependencies = {
            "service_registry": f"unhealthy: {str(e)}",
            "registered_services": 0,
            "healthy_services": 0,
        }

    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow(),
        "uptime_seconds": uptime,
        "dependencies": dependencies,
        "configuration": {
            "debug": settings.debug,
            "rate_limiting_enabled": settings.rate_limit_requests > 0,
            "circuit_breaker_enabled": settings.circuit_breaker_failure_threshold > 0,
        },
    }


@router.get("/health/ready")
async def readiness_check() -> Dict:
    """
    Kubernetes readiness probe endpoint.

    Returns 200 if the service is ready to accept traffic.
    """
    return {"status": "ready", "timestamp": datetime.utcnow()}


@router.get("/health/live")
async def liveness_check() -> Dict:
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if the service is alive.
    """
    return {"status": "alive", "timestamp": datetime.utcnow()}
