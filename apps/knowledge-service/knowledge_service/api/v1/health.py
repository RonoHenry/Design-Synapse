"""Health check endpoints for the Knowledge Service."""
import os
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from packages.common.monitoring.health import get_health_aggregator
from packages.common.service_registry.models import HealthStatus

from ...core.config import settings
from ...infrastructure.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "knowledge-service",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with dependency status."""
    health_data = {
        "service": "knowledge-service",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "checks": {},
    }

    overall_healthy = True

    # Database health check
    try:
        db.execute(text("SELECT 1"))
        health_data["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful",
        }
    except Exception as e:
        health_data["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
        }
        overall_healthy = False

    # Vector search health check (Pinecone)
    try:
        if settings.vector.provider and settings.vector.api_key:
            # Check Pinecone configuration
            if settings.vector.provider.value == "pinecone":
                health_data["checks"]["pinecone"] = {
                    "status": "healthy",
                    "message": "Pinecone configuration available",
                    "provider": settings.vector.provider.value,
                    "environment": settings.vector.environment or "not_specified",
                }
            else:
                health_data["checks"]["vector_search"] = {
                    "status": "healthy",
                    "message": f"Vector search configured with {settings.vector.provider.value}",
                }
        else:
            health_data["checks"]["vector_search"] = {
                "status": "disabled",
                "message": "Vector search service not configured",
            }
    except Exception as e:
        health_data["checks"]["vector_search"] = {
            "status": "unhealthy",
            "message": f"Vector search service check failed: {str(e)}",
        }
        overall_healthy = False

    # LLM service health check (OpenAI)
    try:
        if settings.llm.primary_provider:
            provider_config = settings.llm.get_provider_config(
                settings.llm.primary_provider
            )
            if provider_config and provider_config.get("api_key"):
                health_data["checks"]["llm_service"] = {
                    "status": "healthy",
                    "message": f"LLM service configured with {settings.llm.primary_provider.value}",
                    "primary_provider": settings.llm.primary_provider.value,
                    "fallback_providers": [
                        p.value for p in settings.llm.fallback_providers
                    ],
                }
            else:
                health_data["checks"]["llm_service"] = {
                    "status": "unhealthy",
                    "message": f"LLM provider {settings.llm.primary_provider.value} missing API key",
                }
                overall_healthy = False
        else:
            health_data["checks"]["llm_service"] = {
                "status": "disabled",
                "message": "LLM service not configured",
            }
    except Exception as e:
        health_data["checks"]["llm_service"] = {
            "status": "unhealthy",
            "message": f"LLM service check failed: {str(e)}",
        }
        overall_healthy = False

    # File storage health check
    try:
        storage_path = os.getenv("STORAGE_PATH", "./storage")
        if os.path.exists(storage_path) and os.access(storage_path, os.W_OK):
            health_data["checks"]["file_storage"] = {
                "status": "healthy",
                "message": "File storage accessible",
            }
        else:
            health_data["checks"]["file_storage"] = {
                "status": "unhealthy",
                "message": "File storage not accessible",
            }
            overall_healthy = False
    except Exception as e:
        health_data["checks"]["file_storage"] = {
            "status": "unhealthy",
            "message": f"File storage check failed: {str(e)}",
        }
        overall_healthy = False

    # Set overall status
    health_data["status"] = "healthy" if overall_healthy else "unhealthy"

    # Return appropriate HTTP status
    if not overall_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_data
        )

    return health_data


@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness check that verifies database connectivity and external service availability."""
    checks = {}
    overall_ready = True

    try:
        # Check database connection
        db.execute(text("SELECT 1"))
        checks["database"] = {
            "status": "ready",
            "message": "Database connection successful",
        }
    except Exception as e:
        checks["database"] = {
            "status": "not_ready",
            "message": f"Database connection failed: {str(e)}",
        }
        overall_ready = False

    # Check critical storage dependencies
    try:
        storage_path = settings.file_processing.storage_path
        temp_path = settings.file_processing.temp_path

        for path_name, path in [("storage", storage_path), ("temp", temp_path)]:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)

        checks["file_storage"] = {
            "status": "ready",
            "message": "File storage paths available",
        }
    except Exception as e:
        checks["file_storage"] = {
            "status": "not_ready",
            "message": f"File storage setup failed: {str(e)}",
        }
        overall_ready = False

    # Check Pinecone availability (if configured)
    try:
        if settings.vector.provider and settings.vector.api_key:
            if settings.vector.provider.value == "pinecone":
                # Basic configuration check for Pinecone
                if settings.vector.environment and settings.vector.index_name:
                    checks["pinecone"] = {
                        "status": "ready",
                        "message": "Pinecone configuration available",
                    }
                else:
                    checks["pinecone"] = {
                        "status": "not_ready",
                        "message": "Pinecone configuration incomplete (missing environment or index)",
                    }
                    overall_ready = False
            else:
                checks["vector_search"] = {
                    "status": "ready",
                    "message": f"Vector search configured with {settings.vector.provider.value}",
                }
        else:
            checks["vector_search"] = {
                "status": "disabled",
                "message": "Vector search not configured",
            }
    except Exception as e:
        checks["vector_search"] = {
            "status": "not_ready",
            "message": f"Vector search check failed: {str(e)}",
        }
        overall_ready = False

    # Check OpenAI availability (if configured)
    try:
        if settings.llm.primary_provider:
            provider_config = settings.llm.get_provider_config(
                settings.llm.primary_provider
            )
            if provider_config and provider_config.get("api_key"):
                checks["openai"] = {
                    "status": "ready",
                    "message": f"LLM service configured with {settings.llm.primary_provider.value}",
                }
            else:
                checks["openai"] = {
                    "status": "not_ready",
                    "message": f"LLM provider {settings.llm.primary_provider.value} missing API key",
                }
                overall_ready = False
        else:
            checks["llm_service"] = {
                "status": "disabled",
                "message": "LLM service not configured",
            }
    except Exception as e:
        checks["llm_service"] = {
            "status": "not_ready",
            "message": f"LLM service check failed: {str(e)}",
        }
        overall_ready = False

    response_data = {
        "status": "ready" if overall_ready else "not_ready",
        "service": "knowledge-service",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }

    if not overall_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=response_data
        )

    return response_data


@router.get("/health/live")
async def liveness_check():
    """Liveness check for Kubernetes."""
    return {
        "status": "alive",
        "service": "knowledge-service",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """Get service metrics."""
    try:
        # Get basic database metrics
        resource_count = db.execute(text("SELECT COUNT(*) FROM resources")).scalar()
        topic_count = db.execute(text("SELECT COUNT(*) FROM topics")).scalar()
        bookmark_count = db.execute(text("SELECT COUNT(*) FROM bookmarks")).scalar()

        return {
            "service": "knowledge-service",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "resources_total": resource_count,
                "topics_total": topic_count,
                "bookmarks_total": bookmark_count,
                "uptime_seconds": 0,  # This would be calculated from service start time
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve metrics: {str(e)}",
        )


@router.get("/health/dependencies")
async def check_dependencies():
    """Check health of external dependencies."""
    health_aggregator = get_health_aggregator()

    # Define external services to check
    services = [
        {
            "name": "user-service",
            "health_endpoint": os.getenv("USER_SERVICE_URL", "http://user-service:8000")
            + "/health",
        },
        {
            "name": "project-service",
            "health_endpoint": os.getenv(
                "PROJECT_SERVICE_URL", "http://project-service:8000"
            )
            + "/health",
        },
    ]

    try:
        system_health = await health_aggregator.check_all_services_health(services)

        return {
            "service": "knowledge-service",
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": {
                "overall_status": system_health.overall_status.value,
                "services": [
                    {
                        "name": service.service_name,
                        "status": service.status.value,
                        "message": service.message,
                        "response_time_ms": service.response_time_ms,
                        "last_check": service.timestamp.isoformat(),
                    }
                    for service in system_health.services
                ],
            },
        }
    except Exception as e:
        return {
            "service": "knowledge-service",
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": {
                "overall_status": "error",
                "error": str(e),
                "services": [],
            },
        }
