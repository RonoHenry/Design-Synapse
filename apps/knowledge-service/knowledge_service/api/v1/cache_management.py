"""
Cache management API endpoints for vector search caching.

This module provides REST API endpoints for managing and monitoring
the vector search cache system.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ...core.vector_search import get_vector_search_service
from ...interfaces.services import IVectorSearchService
from ...services.cache_optimizer import CacheHealthChecker, CacheOptimizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/stats", response_model=Dict[str, Any])
async def get_cache_stats(
    vector_service: IVectorSearchService = Depends(get_vector_search_service),
) -> Dict[str, Any]:
    """Get comprehensive cache statistics."""
    try:
        return vector_service.get_cache_stats()
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve cache statistics"
        )


@router.get("/health", response_model=Dict[str, Any])
async def check_cache_health(
    vector_service: IVectorSearchService = Depends(get_vector_search_service),
) -> Dict[str, Any]:
    """Perform comprehensive cache health check."""
    try:
        health_checker = CacheHealthChecker(vector_service)
        return await health_checker.check_cache_health()
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        raise HTTPException(status_code=500, detail="Cache health check failed")


@router.get("/diagnostics", response_model=Dict[str, Any])
async def run_cache_diagnostics(
    vector_service: IVectorSearchService = Depends(get_vector_search_service),
) -> Dict[str, Any]:
    """Run detailed cache diagnostics."""
    try:
        health_checker = CacheHealthChecker(vector_service)
        return await health_checker.run_cache_diagnostics()
    except Exception as e:
        logger.error(f"Cache diagnostics failed: {e}")
        raise HTTPException(status_code=500, detail="Cache diagnostics failed")


@router.post("/clear")
async def clear_cache(
    vector_service: IVectorSearchService = Depends(get_vector_search_service),
) -> Dict[str, str]:
    """Clear all cache entries."""
    try:
        vector_service.clear_cache()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@router.post("/invalidate/user/{user_id}")
async def invalidate_user_cache(
    user_id: str,
    vector_service: IVectorSearchService = Depends(get_vector_search_service),
) -> Dict[str, str]:
    """Invalidate cache entries for a specific user."""
    try:
        vector_service.invalidate_user_cache(user_id)
        return {"message": f"Cache invalidated for user: {user_id}"}
    except Exception as e:
        logger.error(f"Failed to invalidate user cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to invalidate user cache")


@router.post("/invalidate/project/{project_id}")
async def invalidate_project_cache(
    project_id: str,
    vector_service: IVectorSearchService = Depends(get_vector_search_service),
) -> Dict[str, str]:
    """Invalidate cache entries for a specific project."""
    try:
        vector_service.invalidate_project_cache(project_id)
        return {"message": f"Cache invalidated for project: {project_id}"}
    except Exception as e:
        logger.error(f"Failed to invalidate project cache: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to invalidate project cache"
        )


@router.post("/optimize")
async def optimize_cache(
    background_tasks: BackgroundTasks,
    vector_service: IVectorSearchService = Depends(get_vector_search_service),
) -> Dict[str, str]:
    """Analyze and optimize cache performance."""
    try:
        optimizer = CacheOptimizer(vector_service)

        # Run optimization in background
        background_tasks.add_task(optimizer.analyze_and_optimize)

        return {"message": "Cache optimization started in background"}
    except Exception as e:
        logger.error(f"Failed to start cache optimization: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to start cache optimization"
        )


@router.post("/warm-up")
async def warm_up_cache(
    queries: List[str],
    user_filters: Optional[List[Dict[str, str]]] = None,
    background_tasks: BackgroundTasks = None,
    vector_service: IVectorSearchService = Depends(get_vector_search_service),
) -> Dict[str, Any]:
    """Warm up cache with common queries."""
    if not queries:
        raise HTTPException(status_code=400, detail="Queries list cannot be empty")

    if len(queries) > 100:
        raise HTTPException(status_code=400, detail="Too many queries (max 100)")

    try:
        if background_tasks:
            # Run in background for large requests
            background_tasks.add_task(
                vector_service.warm_up_cache, queries, user_filters
            )
            return {
                "message": "Cache warm-up started in background",
                "queries_count": len(queries),
            }
        else:
            # Run synchronously for small requests
            await vector_service.warm_up_cache(queries, user_filters)
            return {"message": "Cache warm-up completed", "queries_count": len(queries)}
    except Exception as e:
        logger.error(f"Cache warm-up failed: {e}")
        raise HTTPException(status_code=500, detail="Cache warm-up failed")


@router.post("/configure")
async def configure_cache(
    enable_search_cache: Optional[bool] = None,
    search_cache_ttl: Optional[int] = None,
    enable_compression: Optional[bool] = None,
    max_search_cache_size: Optional[int] = None,
    max_embedding_cache_size: Optional[int] = None,
    vector_service: IVectorSearchService = Depends(get_vector_search_service),
) -> Dict[str, str]:
    """Configure cache settings."""
    try:
        # Build configuration dict with only provided values
        config_kwargs = {}
        if enable_search_cache is not None:
            config_kwargs["enable_search_cache"] = enable_search_cache
        if search_cache_ttl is not None:
            if search_cache_ttl < 60 or search_cache_ttl > 86400:  # 1 min to 24 hours
                raise HTTPException(
                    status_code=400, detail="TTL must be between 60 and 86400 seconds"
                )
            config_kwargs["search_cache_ttl"] = search_cache_ttl
        if enable_compression is not None:
            config_kwargs["enable_compression"] = enable_compression
        if max_search_cache_size is not None:
            if max_search_cache_size < 100 or max_search_cache_size > 50000:
                raise HTTPException(
                    status_code=400,
                    detail="Search cache size must be between 100 and 50000",
                )
            config_kwargs["max_search_cache_size"] = max_search_cache_size
        if max_embedding_cache_size is not None:
            if max_embedding_cache_size < 50 or max_embedding_cache_size > 25000:
                raise HTTPException(
                    status_code=400,
                    detail="Embedding cache size must be between 50 and 25000",
                )
            config_kwargs["max_embedding_cache_size"] = max_embedding_cache_size

        if not config_kwargs:
            raise HTTPException(
                status_code=400, detail="No configuration parameters provided"
            )

        vector_service.configure_cache(**config_kwargs)
        return {"message": "Cache configuration updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to configure cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to configure cache")


@router.get("/optimization/history", response_model=List[Dict[str, Any]])
async def get_optimization_history(
    vector_service: IVectorSearchService = Depends(get_vector_search_service),
) -> List[Dict[str, Any]]:
    """Get cache optimization history."""
    try:
        optimizer = CacheOptimizer(vector_service)
        return optimizer.get_optimization_history()
    except Exception as e:
        logger.error(f"Failed to get optimization history: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve optimization history"
        )


@router.post("/preload/intelligent")
async def intelligent_cache_preload(
    recent_queries: List[str],
    user_project_mapping: Optional[Dict[str, List[str]]] = None,
    background_tasks: BackgroundTasks = None,
    vector_service: IVectorSearchService = Depends(get_vector_search_service),
) -> Dict[str, Any]:
    """Intelligently preload cache based on usage patterns."""
    if not recent_queries:
        raise HTTPException(
            status_code=400, detail="Recent queries list cannot be empty"
        )

    if len(recent_queries) > 200:
        raise HTTPException(status_code=400, detail="Too many queries (max 200)")

    try:
        optimizer = CacheOptimizer(vector_service)

        if background_tasks:
            # Run in background for large requests
            background_tasks.add_task(
                optimizer.preload_cache_intelligently,
                recent_queries,
                user_project_mapping,
            )
            return {
                "message": "Intelligent cache preloading started in background",
                "queries_count": len(recent_queries),
            }
        else:
            # Run synchronously
            result = await optimizer.preload_cache_intelligently(
                recent_queries, user_project_mapping
            )
            return result
    except Exception as e:
        logger.error(f"Intelligent cache preload failed: {e}")
        raise HTTPException(status_code=500, detail="Intelligent cache preload failed")
