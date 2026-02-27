"""Health check endpoints for monitoring service health."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional

import httpx
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.cache import get_redis_client
from src.core.config import settings
from src.core.database import get_db
from src.core.metrics import get_metrics_collector

router = APIRouter()


async def check_database_health() -> Dict[str, any]:
    """Check database connectivity and health."""
    try:
        start_time = datetime.now(timezone.utc)

        # Get database session
        async for db in get_db():
            try:
                # Execute simple query
                result = await db.execute(text("SELECT 1 as health_check"))
                result.fetchone()

                # Get database version
                version_result = await db.execute(text("SELECT VERSION() as version"))
                version_row = version_result.fetchone()
                db_version = version_row[0] if version_row else None

                end_time = datetime.now(timezone.utc)
                response_time_ms = (end_time - start_time).total_seconds() * 1000

                return {
                    "status": "healthy",
                    "message": "Database connection successful",
                    "response_time_ms": round(response_time_ms, 2),
                    "database_version": db_version,
                }
            finally:
                await db.close()

    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
            "error": str(e),
        }


async def check_redis_health() -> Dict[str, any]:
    """Check Redis connectivity and health."""
    try:
        start_time = datetime.now(timezone.utc)

        redis_client = await get_redis_client()

        # Ping Redis
        await redis_client.ping()

        # Get Redis info
        info = await redis_client.info()
        redis_version = info.get("redis_version", "unknown")

        end_time = datetime.now(timezone.utc)
        response_time_ms = (end_time - start_time).total_seconds() * 1000

        return {
            "status": "healthy",
            "message": "Redis connection successful",
            "response_time_ms": round(response_time_ms, 2),
            "redis_version": redis_version,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}",
            "error": str(e),
        }


async def check_external_service_health(
    service_name: str, service_url: str, timeout: int = 5
) -> Dict[str, any]:
    """Check external service availability."""
    try:
        start_time = datetime.now(timezone.utc)

        # Try to reach the service health endpoint
        health_endpoint = f"{service_url}/health"

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(health_endpoint)

            end_time = datetime.now(timezone.utc)
            response_time_ms = (end_time - start_time).total_seconds() * 1000

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "message": f"{service_name} is available",
                    "response_time_ms": round(response_time_ms, 2),
                    "service_url": service_url,
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": f"{service_name} returned status {response.status_code}",
                    "response_time_ms": round(response_time_ms, 2),
                    "service_url": service_url,
                    "status_code": response.status_code,
                }
    except httpx.TimeoutException:
        return {
            "status": "unhealthy",
            "message": f"{service_name} request timed out",
            "service_url": service_url,
            "error": "Timeout",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"{service_name} is unavailable: {str(e)}",
            "service_url": service_url,
            "error": str(e),
        }


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Comprehensive health check endpoint.

    Checks:
    - Database connectivity
    - Redis connectivity
    - External service availability (Design, Knowledge, Project, Vendor services)

    Returns:
        Health status with details for each component
    """
    # Run all health checks concurrently
    db_health_task = check_database_health()
    redis_health_task = check_redis_health()
    design_service_task = check_external_service_health(
        "Design Service", settings.design_service_url
    )
    knowledge_service_task = check_external_service_health(
        "Knowledge Service", settings.knowledge_service_url
    )
    project_service_task = check_external_service_health(
        "Project Service", settings.project_service_url
    )
    vendor_service_task = check_external_service_health(
        "Vendor Service", settings.vendor_service_url
    )

    # Gather all results
    (
        db_health,
        redis_health,
        design_service_health,
        knowledge_service_health,
        project_service_health,
        vendor_service_health,
    ) = await asyncio.gather(
        db_health_task,
        redis_health_task,
        design_service_task,
        knowledge_service_task,
        project_service_task,
        vendor_service_task,
        return_exceptions=True,
    )

    # Handle any exceptions from health checks
    def handle_exception(result, component_name):
        if isinstance(result, Exception):
            return {
                "status": "unhealthy",
                "message": f"{component_name} health check failed",
                "error": str(result),
            }
        return result

    db_health = handle_exception(db_health, "Database")
    redis_health = handle_exception(redis_health, "Redis")
    design_service_health = handle_exception(design_service_health, "Design Service")
    knowledge_service_health = handle_exception(
        knowledge_service_health, "Knowledge Service"
    )
    project_service_health = handle_exception(project_service_health, "Project Service")
    vendor_service_health = handle_exception(vendor_service_health, "Vendor Service")

    # Determine overall health status
    all_components = [
        db_health,
        redis_health,
        design_service_health,
        knowledge_service_health,
        project_service_health,
        vendor_service_health,
    ]

    unhealthy_count = sum(
        1 for component in all_components if component.get("status") == "unhealthy"
    )

    # Overall status is healthy only if all components are healthy
    overall_status = "healthy" if unhealthy_count == 0 else "unhealthy"

    # Determine HTTP status code
    http_status = (
        status.HTTP_200_OK
        if overall_status == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    response_data = {
        "status": overall_status,
        "service": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "components": {
            "database": db_health,
            "redis": redis_health,
            "external_services": {
                "design_service": design_service_health,
                "knowledge_service": knowledge_service_health,
                "project_service": project_service_health,
                "vendor_service": vendor_service_health,
            },
        },
        "summary": {
            "total_components": len(all_components),
            "healthy_components": len(all_components) - unhealthy_count,
            "unhealthy_components": unhealthy_count,
        },
    }

    return JSONResponse(status_code=http_status, content=response_data)


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """
    Liveness probe endpoint.

    Simple check to verify the service is running.
    Used by orchestrators (Kubernetes, Docker Swarm) to determine if the service should be restarted.

    Returns:
        Simple status indicating the service is alive
    """
    return {
        "status": "alive",
        "service": settings.app_name,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """
    Readiness probe endpoint.

    Checks if the service is ready to accept traffic.
    Verifies critical dependencies (database and Redis) are available.
    Used by orchestrators to determine if traffic should be routed to this instance.

    Returns:
        Readiness status with critical component checks
    """
    # Check only critical components for readiness
    db_health_task = check_database_health()
    redis_health_task = check_redis_health()

    db_health, redis_health = await asyncio.gather(
        db_health_task, redis_health_task, return_exceptions=True
    )

    # Handle exceptions
    if isinstance(db_health, Exception):
        db_health = {
            "status": "unhealthy",
            "message": "Database health check failed",
            "error": str(db_health),
        }

    if isinstance(redis_health, Exception):
        redis_health = {
            "status": "unhealthy",
            "message": "Redis health check failed",
            "error": str(redis_health),
        }

    # Service is ready only if both database and Redis are healthy
    is_ready = (
        db_health.get("status") == "healthy" and redis_health.get("status") == "healthy"
    )

    http_status = (
        status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    response_data = {
        "status": "ready" if is_ready else "not_ready",
        "service": settings.app_name,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "components": {
            "database": db_health,
            "redis": redis_health,
        },
    }

    return JSONResponse(status_code=http_status, content=response_data)


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def get_metrics():
    """
    Get service metrics.

    Returns comprehensive metrics including:
    - Request latency percentiles (p50, p95, p99)
    - Error rates by endpoint
    - External service call metrics
    - Cache hit/miss rates
    - Service uptime

    Returns:
        Metrics summary with performance data
    """
    metrics_collector = get_metrics_collector()
    metrics_summary = metrics_collector.get_metrics_summary()

    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "metrics": metrics_summary,
    }


@router.get("/metrics/endpoints/{endpoint:path}", status_code=status.HTTP_200_OK)
async def get_endpoint_metrics(endpoint: str):
    """
    Get metrics for a specific endpoint.

    Args:
        endpoint: Endpoint path (e.g., /api/v1/designs)

    Returns:
        Endpoint-specific metrics
    """
    metrics_collector = get_metrics_collector()
    endpoint_metrics = metrics_collector.get_endpoint_metrics(f"/{endpoint}")

    return {
        "service": settings.app_name,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "metrics": endpoint_metrics,
    }


@router.get("/metrics/services/{service_name}", status_code=status.HTTP_200_OK)
async def get_service_metrics(service_name: str):
    """
    Get metrics for a specific external service.

    Args:
        service_name: Service name (e.g., Design Service, Knowledge Service)

    Returns:
        Service-specific metrics
    """
    metrics_collector = get_metrics_collector()
    service_metrics = metrics_collector.get_service_metrics(service_name)

    return {
        "service": settings.app_name,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "metrics": service_metrics,
    }
