"""API endpoints for Service Registry."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .models import (HealthStatus, ServiceDiscoveryFilter, ServiceEndpoint,
                     ServiceRegistrationRequest, SystemHealthStatus)
from .registry import ServiceRegistry, get_service_registry

router = APIRouter(prefix="/registry", tags=["service-registry"])


class ServiceRegistrationResponse(BaseModel):
    """Response model for service registration."""

    instance_id: str
    message: str


class ServiceDeregistrationRequest(BaseModel):
    """Request model for service deregistration."""

    service_name: str
    instance_id: Optional[str] = None


@router.post("/register", response_model=ServiceRegistrationResponse)
async def register_service(
    request: ServiceRegistrationRequest,
    registry: ServiceRegistry = Depends(get_service_registry),
):
    """
    Register a service with the registry.

    Args:
        request: Service registration request
        registry: Service registry instance

    Returns:
        Registration response with instance ID
    """
    try:
        instance_id = await registry.register_service(request)
        return ServiceRegistrationResponse(
            instance_id=instance_id,
            message=f"Service {request.service.name} registered successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to register service: {str(e)}"
        )


@router.post("/deregister")
async def deregister_service(
    request: ServiceDeregistrationRequest,
    registry: ServiceRegistry = Depends(get_service_registry),
):
    """
    Deregister a service from the registry.

    Args:
        request: Service deregistration request
        registry: Service registry instance

    Returns:
        Success message
    """
    try:
        success = await registry.deregister_service(
            request.service_name, request.instance_id
        )

        if not success:
            raise HTTPException(
                status_code=404, detail=f"Service {request.service_name} not found"
            )

        return {"message": f"Service {request.service_name} deregistered successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to deregister service: {str(e)}"
        )


@router.get("/discover", response_model=List[ServiceEndpoint])
async def discover_services(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    health_status: Optional[HealthStatus] = Query(
        None, description="Filter by health status"
    ),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
    min_response_time: Optional[float] = Query(
        None, description="Minimum response time filter"
    ),
    max_response_time: Optional[float] = Query(
        None, description="Maximum response time filter"
    ),
    registry: ServiceRegistry = Depends(get_service_registry),
):
    """
    Discover services based on filter criteria.

    Args:
        service_name: Optional service name filter
        health_status: Optional health status filter
        tags: Optional comma-separated tags filter
        min_response_time: Optional minimum response time filter
        max_response_time: Optional maximum response time filter
        registry: Service registry instance

    Returns:
        List of matching service endpoints
    """
    try:
        # Build filter criteria
        filter_criteria = ServiceDiscoveryFilter(
            service_name=service_name,
            health_status=health_status,
            tags=tags.split(",") if tags else [],
            min_response_time=min_response_time,
            max_response_time=max_response_time,
        )

        endpoints = await registry.discover_services(filter_criteria)
        return endpoints

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to discover services: {str(e)}"
        )


@router.get(
    "/services/{service_name}/healthy", response_model=Optional[ServiceEndpoint]
)
async def get_healthy_endpoint(
    service_name: str, registry: ServiceRegistry = Depends(get_service_registry)
):
    """
    Get a healthy endpoint for a specific service.

    Args:
        service_name: Name of the service
        registry: Service registry instance

    Returns:
        Healthy service endpoint or None
    """
    try:
        endpoint = await registry.get_healthy_endpoint(service_name)
        return endpoint

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get healthy endpoint: {str(e)}"
        )


@router.get("/services/{service_name}/instances", response_model=List[ServiceEndpoint])
async def get_service_instances(
    service_name: str, registry: ServiceRegistry = Depends(get_service_registry)
):
    """
    Get all instances of a specific service.

    Args:
        service_name: Name of the service
        registry: Service registry instance

    Returns:
        List of service instances
    """
    try:
        instances = await registry.get_service_instances(service_name)
        return instances

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get service instances: {str(e)}"
        )


@router.get("/health", response_model=SystemHealthStatus)
async def get_system_health(registry: ServiceRegistry = Depends(get_service_registry)):
    """
    Get overall system health status.

    Args:
        registry: Service registry instance

    Returns:
        System health status
    """
    try:
        health_status = await registry.get_system_health()
        return health_status

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get system health: {str(e)}"
        )


@router.get("/services", response_model=dict)
async def get_all_services(registry: ServiceRegistry = Depends(get_service_registry)):
    """
    Get all registered services.

    Args:
        registry: Service registry instance

    Returns:
        Dictionary mapping service names to their instances
    """
    try:
        services = await registry.get_all_services()
        return services

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get all services: {str(e)}"
        )
