"""Vector search service for knowledge resources with enhanced caching."""

import os
import time
import hashlib
import json
import pickle
import gzip
from typing import Dict, List, Optional, Any, Union
import pinecone
from sentence_transformers import SentenceTransformer
import logging
from datetime import datetime, timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from ..interfaces.services import IVectorSearchService
from ..exceptions import (
    VectorSearchError, IndexingError, SearchQueryError, 
    MetadataValidationError
)
from ..config import get_config
from ..core.error_handling import handle_service_errors, error_context, ErrorRecovery

logger = logging.getLogger(__name__)


class DistributedSearchCache:
    """Enhanced distributed cache for search results with Redis support and compression."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600, redis_url: Optional[str] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.enabled = True
        self.use_compression = True
        self.cache_prefix = "knowledge_search:"
        
        # Initialize Redis if available and configured
        self.redis_client = None
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}, falling back to in-memory")
                self.redis_client = None
        
        # Fallback to in-memory cache
        if not self.redis_client:
            self.cache = {}
            self.access_times = {}
            logger.info("Using in-memory cache for search results")
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "compression_ratio": 0.0
        }
    
    def _generate_key(self, query: str, filter_metadata: Optional[Dict], top_k: int, user_id: Optional[str] = None) -> str:
        """Generate cache key from search parameters with optional user partitioning."""
        key_data = {
            "query": query.lower().strip(),  # Normalize query
            "filter": filter_metadata or {},
            "top_k": top_k,
            "user_id": user_id  # For user-specific caching
        }
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{self.cache_prefix}{key_hash}"
    
    def _compress_data(self, data: Any) -> bytes:
        """Compress data using gzip if compression is enabled."""
        if not self.use_compression:
            return pickle.dumps(data)
        
        pickled_data = pickle.dumps(data)
        compressed_data = gzip.compress(pickled_data)
        
        # Update compression ratio stats
        if len(pickled_data) > 0:
            ratio = len(compressed_data) / len(pickled_data)
            self.stats["compression_ratio"] = (self.stats["compression_ratio"] + ratio) / 2
        
        return compressed_data
    
    def _decompress_data(self, data: bytes) -> Any:
        """Decompress data using gzip if compression is enabled."""
        if not self.use_compression:
            return pickle.loads(data)
        
        try:
            decompressed_data = gzip.decompress(data)
            return pickle.loads(decompressed_data)
        except gzip.BadGzipFile:
            # Fallback for uncompressed data
            return pickle.loads(data)
    
    def get(self, query: str, filter_metadata: Optional[Dict], top_k: int, user_id: Optional[str] = None) -> Optional[List[Dict]]:
        """Get cached search results with Redis or in-memory fallback."""
        if not self.enabled:
            return None
        
        key = self._generate_key(query, filter_metadata, top_k, user_id)
        
        try:
            if self.redis_client:
                # Redis-based cache
                cached_data = self.redis_client.get(key)
                if cached_data:
                    results = self._decompress_data(cached_data)
                    self.stats["hits"] += 1
                    logger.debug(f"Redis cache hit for search query: {query[:50]}...")
                    return results
            else:
                # In-memory cache
                if key in self.cache:
                    entry = self.cache[key]
                    
                    # Check if entry has expired
                    if time.time() - entry["timestamp"] > entry["ttl"]:
                        del self.cache[key]
                        if key in self.access_times:
                            del self.access_times[key]
                        self.stats["misses"] += 1
                        return None
                    
                    # Update access time
                    self.access_times[key] = time.time()
                    self.stats["hits"] += 1
                    logger.debug(f"Memory cache hit for search query: {query[:50]}...")
                    return entry["results"]
            
            self.stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            self.stats["misses"] += 1
            return None
    
    def set(self, query: str, filter_metadata: Optional[Dict], top_k: int, results: List[Dict], ttl: Optional[int] = None, user_id: Optional[str] = None):
        """Cache search results with Redis or in-memory fallback."""
        if not self.enabled:
            return
        
        key = self._generate_key(query, filter_metadata, top_k, user_id)
        ttl = ttl or self.default_ttl
        
        try:
            if self.redis_client:
                # Redis-based cache with compression
                compressed_data = self._compress_data(results)
                self.redis_client.setex(key, ttl, compressed_data)
                logger.debug(f"Cached search results in Redis for query: {query[:50]}...")
            else:
                # In-memory cache
                # Evict old entries if cache is full
                if len(self.cache) >= self.max_size:
                    self._evict_lru()
                
                self.cache[key] = {
                    "results": results,
                    "timestamp": time.time(),
                    "ttl": ttl
                }
                self.access_times[key] = time.time()
                logger.debug(f"Cached search results in memory for query: {query[:50]}...")
            
            self.stats["sets"] += 1
            
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    def _evict_lru(self):
        """Evict least recently used entries from in-memory cache."""
        if not self.access_times:
            return
        
        # Remove 10% of entries (LRU)
        num_to_remove = max(1, len(self.access_times) // 10)
        lru_keys = sorted(self.access_times.keys(), key=lambda k: self.access_times[k])[:num_to_remove]
        
        for key in lru_keys:
            if key in self.cache:
                del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
        
        self.stats["evictions"] += len(lru_keys)
        logger.debug(f"Evicted {len(lru_keys)} LRU cache entries")
    
    def clear(self):
        """Clear all cached entries."""
        try:
            if self.redis_client:
                # Clear Redis cache entries with our prefix
                keys = self.redis_client.keys(f"{self.cache_prefix}*")
                if keys:
                    self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} Redis cache entries")
            else:
                # Clear in-memory cache
                self.cache.clear()
                self.access_times.clear()
                logger.info("Cleared in-memory search cache")
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching a pattern."""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(f"{self.cache_prefix}*{pattern}*")
                if keys:
                    self.redis_client.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} cache entries matching pattern: {pattern}")
            else:
                # For in-memory cache, we need to check each key
                keys_to_remove = [key for key in self.cache.keys() if pattern in key]
                for key in keys_to_remove:
                    if key in self.cache:
                        del self.cache[key]
                    if key in self.access_times:
                        del self.access_times[key]
                logger.info(f"Invalidated {len(keys_to_remove)} in-memory cache entries matching pattern: {pattern}")
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
    
    def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a specific user."""
        self.invalidate_pattern(f'"user_id":"{user_id}"')
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        cache_size = 0
        cache_type = "redis" if self.redis_client else "memory"
        
        try:
            if self.redis_client:
                # Get Redis cache size
                keys = self.redis_client.keys(f"{self.cache_prefix}*")
                cache_size = len(keys)
            else:
                cache_size = len(self.cache)
        except Exception as e:
            logger.warning(f"Error getting cache size: {e}")
        
        hit_rate = 0.0
        total_requests = self.stats["hits"] + self.stats["misses"]
        if total_requests > 0:
            hit_rate = self.stats["hits"] / total_requests
        
        return {
            "enabled": self.enabled,
            "type": cache_type,
            "size": cache_size,
            "max_size": self.max_size,
            "default_ttl": self.default_ttl,
            "use_compression": self.use_compression,
            "hit_rate": hit_rate,
            "compression_ratio": self.stats["compression_ratio"],
            **self.stats
        }


class DistributedEmbeddingCache:
    """Enhanced distributed cache for embeddings with Redis support."""
    
    def __init__(self, max_size: int = 500, redis_url: Optional[str] = None):
        self.max_size = max_size
        self.cache_prefix = "knowledge_embedding:"
        
        # Initialize Redis if available and configured
        self.redis_client = None
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
                self.redis_client.ping()
                logger.info("Redis embedding cache initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis embedding cache: {e}, falling back to in-memory")
                self.redis_client = None
        
        # Fallback to in-memory cache
        if not self.redis_client:
            self.cache = {}
            self.access_times = {}
            logger.info("Using in-memory cache for embeddings")
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0
        }
    
    def _generate_key(self, text: str) -> str:
        """Generate cache key from text."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"{self.cache_prefix}{text_hash}"
    
    def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding with Redis or in-memory fallback."""
        key = self._generate_key(text)
        
        try:
            if self.redis_client:
                # Redis-based cache
                cached_data = self.redis_client.get(key)
                if cached_data:
                    embedding = pickle.loads(cached_data)
                    self.stats["hits"] += 1
                    return embedding
            else:
                # In-memory cache
                if key in self.cache:
                    self.access_times[key] = time.time()
                    self.stats["hits"] += 1
                    return self.cache[key]
            
            self.stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.warning(f"Embedding cache get error: {e}")
            self.stats["misses"] += 1
            return None
    
    def set(self, text: str, embedding: List[float], ttl: int = 86400):  # 24 hours default
        """Cache embedding with Redis or in-memory fallback."""
        key = self._generate_key(text)
        
        try:
            if self.redis_client:
                # Redis-based cache with TTL
                serialized_embedding = pickle.dumps(embedding)
                self.redis_client.setex(key, ttl, serialized_embedding)
            else:
                # In-memory cache
                if len(self.cache) >= self.max_size:
                    self._evict_lru()
                
                self.cache[key] = embedding
                self.access_times[key] = time.time()
            
            self.stats["sets"] += 1
            
        except Exception as e:
            logger.warning(f"Embedding cache set error: {e}")
    
    def _evict_lru(self):
        """Evict least recently used embeddings from in-memory cache."""
        if not self.access_times:
            return
        
        # Remove 20% of entries
        num_to_remove = max(1, len(self.access_times) // 5)
        lru_keys = sorted(self.access_times.keys(), key=lambda k: self.access_times[k])[:num_to_remove]
        
        for key in lru_keys:
            if key in self.cache:
                del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
        
        self.stats["evictions"] += len(lru_keys)
    
    def clear(self):
        """Clear all cached embeddings."""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(f"{self.cache_prefix}*")
                if keys:
                    self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} Redis embedding cache entries")
            else:
                self.cache.clear()
                self.access_times.clear()
                logger.info("Cleared in-memory embedding cache")
        except Exception as e:
            logger.warning(f"Embedding cache clear error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics."""
        cache_size = 0
        cache_type = "redis" if self.redis_client else "memory"
        
        try:
            if self.redis_client:
                keys = self.redis_client.keys(f"{self.cache_prefix}*")
                cache_size = len(keys)
            else:
                cache_size = len(self.cache)
        except Exception as e:
            logger.warning(f"Error getting embedding cache size: {e}")
        
        hit_rate = 0.0
        total_requests = self.stats["hits"] + self.stats["misses"]
        if total_requests > 0:
            hit_rate = self.stats["hits"] / total_requests
        
        return {
            "type": cache_type,
            "size": cache_size,
            "max_size": self.max_size,
            "hit_rate": hit_rate,
            **self.stats
        }


class VectorSearchService(IVectorSearchService):
    """Service for managing vector search operations with caching."""

    def __init__(self, config = None):
        """Initialize vector search service."""
        from ..config import get_config
        self.config = config or get_config()
        
        # Initialize enhanced caching
        search_config = self.config.get_search_config()
        redis_url = search_config.get("redis_url") or os.getenv("REDIS_URL")
        
        self.search_cache = DistributedSearchCache(
            max_size=search_config.get("search_cache_max_size", 1000),
            default_ttl=search_config.get("cache_ttl_minutes", 60) * 60,
            redis_url=redis_url
        )
        self.search_cache.enabled = search_config.get("enable_search_cache", True)
        self.search_cache.use_compression = search_config.get("enable_cache_compression", True)
        
        self.embedding_cache = DistributedEmbeddingCache(
            max_size=search_config.get("embedding_cache_max_size", 500),
            redis_url=redis_url
        )
        
        # Performance metrics
        self.metrics = {
            "search_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "embedding_cache_hits": 0,
            "embedding_cache_misses": 0,
            "total_search_time": 0.0,
            "avg_search_time": 0.0
        }
        
        # Initialize Pinecone
        vector_config = self.config.vector.get_provider_config()
        api_key = vector_config.get("api_key") or os.getenv("PINECONE_API_KEY")
        environment = vector_config.get("environment") or os.getenv("PINECONE_ENVIRONMENT")
        
        if not api_key or not environment:
            logger.warning("Pinecone credentials not configured")
            raise VectorSearchError("Pinecone API key and environment must be configured")
        
        try:
            pinecone.init(api_key=api_key, environment=environment)
            logger.info("Pinecone initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise VectorSearchError(f"Failed to initialize Pinecone: {str(e)}")
        
        self.index_name = vector_config.get("index_name", "knowledge-resources")
        self.dimension = vector_config.get("dimension", 384)

        # Create index if it doesn't exist
        try:
            if self.index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine"
                )
                logger.info(f"Created Pinecone index: {self.index_name}")
            
            # Get the index instance
            self.index = pinecone.Index(self.index_name)
            
        except Exception as e:
            logger.error(f"Failed to setup Pinecone index: {e}")
            raise VectorSearchError(f"Failed to setup Pinecone index: {str(e)}")
        
        # Load the sentence transformer model
        try:
            embedding_config = self.config.vector.get_provider_config()
            model_name = embedding_config.get("embedding_model", "all-MiniLM-L6-v2")
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise VectorSearchError(f"Failed to load embedding model: {str(e)}")
    
    def _generate_embedding_with_cache(self, text: str) -> List[float]:
        """Generate embedding with caching."""
        # Check cache first
        cached_embedding = self.embedding_cache.get(text)
        if cached_embedding is not None:
            self.metrics["embedding_cache_hits"] += 1
            return cached_embedding
        
        # Generate new embedding
        self.metrics["embedding_cache_misses"] += 1
        embedding = self.model.encode(text).tolist()
        
        # Cache the result
        self.embedding_cache.set(text, embedding)
        
        return embedding

    @handle_service_errors("vector_search", "index_resource")
    @ErrorRecovery.with_retry(max_attempts=3, exceptions=(Exception,))
    async def index_resource(
        self,
        resource_id: int,
        title: str,
        description: str,
        content: str,
        metadata: Dict
    ) -> None:
        """Index a resource in Pinecone.
        
        Args:
            resource_id: The ID of the resource
            title: The resource title
            description: The resource description
            content: The extracted text content
            metadata: Additional metadata about the resource
        """
        with error_context(
            "index_resource_validation",
            resource_id=resource_id,
            content_length=len(content)
        ):
            # Validate inputs
            self._validate_resource_id(resource_id)
            self._validate_content(content)
            sanitized_metadata = self._sanitize_metadata(metadata)
        
        with error_context(
            "embedding_generation",
            resource_id=resource_id
        ):
            # Create text to embed (combine relevant fields)
            text_to_embed = f"{title}\n{description}\n{content}"
            
            # Truncate if too long
            if len(text_to_embed) > self.config.max_content_length:
                text_to_embed = text_to_embed[:self.config.max_content_length]
                logger.warning(f"Truncated content for resource {resource_id} to {self.config.max_content_length} characters")
            
            # Generate embedding with caching
            try:
                embedding = self._generate_embedding_with_cache(text_to_embed)
                logger.debug(f"Generated embedding for resource {resource_id}")
            except Exception as e:
                raise IndexingError(f"Embedding generation failed: {str(e)}") from e
        
        with error_context(
            "pinecone_upsert",
            resource_id=resource_id
        ):
            # Upsert to Pinecone
            try:
                self.index.upsert(
                    vectors=[
                        (
                            str(resource_id),
                            embedding,
                            {
                                "title": title,
                                "description": description,
                                **sanitized_metadata
                            }
                        )
                    ]
                )
                logger.info(f"Successfully indexed resource {resource_id}")
                
                # Invalidate related cache entries
                self._invalidate_resource_cache(resource_id, sanitized_metadata)
                
            except Exception as e:
                raise IndexingError(f"Pinecone indexing failed: {str(e)}") from e
    
    @handle_service_errors("vector_search", "search_resources")
    @ErrorRecovery.with_retry(max_attempts=2, exceptions=(Exception,))
    async def search_resources(
        self,
        query: str,
        filter_metadata: Optional[Dict] = None,
        top_k: int = 10
    ) -> List[Dict]:
        """Search for resources using semantic similarity with caching.
        
        Args:
            query: The search query
            filter_metadata: Optional metadata filters
            top_k: Number of results to return
            
        Returns:
            List of matched resources with scores
        """
        start_time = time.time()
        self.metrics["search_requests"] += 1
        
        with error_context(
            "search_validation",
            query_length=len(query),
            top_k=top_k
        ):
            # Validate inputs
            self._validate_query(query)
            if filter_metadata:
                self._validate_filter_metadata(filter_metadata)
        
        # Extract user_id from filter_metadata for user-specific caching
        user_id = filter_metadata.get("user_id") if filter_metadata else None
        
        # Check cache first
        cached_results = self.search_cache.get(query, filter_metadata, top_k, user_id)
        if cached_results is not None:
            self.metrics["cache_hits"] += 1
            search_time = time.time() - start_time
            self.metrics["total_search_time"] += search_time
            self._update_avg_search_time()
            logger.debug(f"Returning cached results for query: {query[:50]}...")
            return cached_results
        
        self.metrics["cache_misses"] += 1
        
        with error_context(
            "query_embedding_generation",
            query_preview=query[:50]
        ):
            try:
                # Generate query embedding with caching
                query_embedding = self._generate_embedding_with_cache(query)
                logger.debug(f"Generated query embedding for: {query[:50]}...")
            except Exception as e:
                raise SearchQueryError(f"Query embedding generation failed: {str(e)}") from e
        
        with error_context(
            "pinecone_search",
            top_k=top_k,
            has_filters=bool(filter_metadata)
        ):
            try:
                # Search in Pinecone
                results = self.index.query(
                    vector=query_embedding,
                    filter=filter_metadata,
                    top_k=top_k,
                    include_metadata=True
                )
                
                # Format and sort results by score (descending)
                formatted_results = [
                    {
                        "resource_id": int(match.id),
                        "score": match.score,
                        "metadata": match.metadata
                    }
                    for match in results.matches
                ]
                
                # Sort by score descending
                formatted_results.sort(key=lambda x: x["score"], reverse=True)
                
                # Cache the results with user-specific caching
                self.search_cache.set(query, filter_metadata, top_k, formatted_results, user_id=user_id)
                
                search_time = time.time() - start_time
                self.metrics["total_search_time"] += search_time
                self._update_avg_search_time()
                
                logger.info(f"Found {len(formatted_results)} results for query (search time: {search_time:.3f}s)")
                return formatted_results
                
            except Exception as e:
                raise SearchQueryError(f"Vector search query failed: {str(e)}") from e
    
    def _update_avg_search_time(self):
        """Update average search time metric."""
        if self.metrics["search_requests"] > 0:
            self.metrics["avg_search_time"] = self.metrics["total_search_time"] / self.metrics["search_requests"]
    
    async def delete_resource(self, resource_id: int) -> None:
        """Delete a resource from the vector index.
        
        Args:
            resource_id: The ID of the resource to delete
        """
        # Validate resource ID
        if not isinstance(resource_id, int) or resource_id <= 0:
            raise ValueError("Invalid resource ID")
        
        try:
            # Delete main resource entry
            self.index.delete(ids=[str(resource_id)])
            
            # Also delete any chunks for this resource
            await self.delete_resource_chunks(resource_id)
            
            # Invalidate cache entries for this resource
            self.search_cache.invalidate_pattern(f'"resource_id":{resource_id}')
            
        except Exception as e:
            # Handle nonexistent resources gracefully
            if "not found" in str(e).lower():
                # Resource doesn't exist, which is fine for delete operation
                pass
            else:
                raise e
    
    async def delete_resource_chunks(self, resource_id: int) -> None:
        """Delete all chunks for a resource from the vector index.
        
        Args:
            resource_id: The ID of the resource whose chunks to delete
        """
        try:
            # Query for all chunks belonging to this resource
            # Note: This is a simplified approach. In production, you might want to
            # maintain a separate index of chunk IDs or use metadata filtering
            
            # For now, we'll try to delete potential chunk IDs
            # This assumes chunks are named as {resource_id}_chunk_{i}
            chunk_ids_to_delete = []
            
            # Try deleting up to 100 potential chunks (should be more than enough)
            for i in range(100):
                chunk_ids_to_delete.append(f"{resource_id}_chunk_{i}")
            
            # Delete in batches to avoid API limits
            batch_size = 10
            for i in range(0, len(chunk_ids_to_delete), batch_size):
                batch = chunk_ids_to_delete[i:i + batch_size]
                try:
                    self.index.delete(ids=batch)
                except Exception as e:
                    # Ignore errors for non-existent chunks
                    if "not found" not in str(e).lower():
                        logger.warning(f"Error deleting chunk batch: {e}")
            
            logger.info(f"Deleted chunks for resource {resource_id}")
            
        except Exception as e:
            logger.warning(f"Error deleting chunks for resource {resource_id}: {e}")
            # Don't raise exception as this is cleanup
    
    async def update_resource(
        self,
        resource_id: int,
        title: str,
        description: str,
        content: str,
        metadata: Dict
    ) -> None:
        """Update a resource in the vector index.
        
        This is implemented as a delete followed by an insert to ensure
        consistency.
        
        Args:
            resource_id: The ID of the resource
            title: The updated title
            description: The updated description
            content: The updated content
            metadata: The updated metadata
        """
        await self.delete_resource(resource_id)
        await self.index_resource(
            resource_id,
            title,
            description,
            content,
            metadata
        )
    
    async def index_resource_chunks(
        self,
        resource_id: int,
        title: str,
        description: str,
        content_chunks: List[str],
        metadata: Dict
    ) -> None:
        """Index a resource using multiple content chunks for better granularity.
        
        Args:
            resource_id: The ID of the resource
            title: The resource title
            description: The resource description
            content_chunks: List of content chunks to index
            metadata: Additional metadata about the resource
        """
        # Validate inputs
        self._validate_resource_id(resource_id)
        if not content_chunks or not any(chunk.strip() for chunk in content_chunks):
            raise MetadataValidationError("Content chunks cannot be empty")
        
        sanitized_metadata = self._sanitize_metadata(metadata)
        
        try:
            vectors_to_upsert = []
            
            for i, chunk in enumerate(content_chunks):
                if not chunk.strip():
                    continue
                
                # Create text to embed (combine title, description, and chunk)
                text_to_embed = f"{title}\n{description}\n{chunk}"
                
                # Truncate if too long
                if len(text_to_embed) > self.config.max_content_length:
                    text_to_embed = text_to_embed[:self.config.max_content_length]
                
                # Generate embedding with caching
                embedding = self._generate_embedding_with_cache(text_to_embed)
                
                # Create unique ID for this chunk
                chunk_id = f"{resource_id}_chunk_{i}"
                
                vectors_to_upsert.append((
                    chunk_id,
                    embedding,
                    {
                        "resource_id": resource_id,
                        "title": title,
                        "description": description,
                        "chunk_index": i,
                        "chunk_content": chunk[:500],  # Store first 500 chars for reference
                        **sanitized_metadata
                    }
                ))
            
            # Batch upsert all chunks
            if vectors_to_upsert:
                self.index.upsert(vectors=vectors_to_upsert)
                logger.info(f"Successfully indexed {len(vectors_to_upsert)} chunks for resource {resource_id}")
            
        except Exception as e:
            logger.error(f"Failed to index resource chunks {resource_id}: {e}")
            if "embedding" in str(e).lower():
                raise IndexingError("Embedding generation failed")
            elif "pinecone" in str(e).lower():
                raise IndexingError("Pinecone indexing failed")
            else:
                raise IndexingError(f"Failed to index resource chunks: {str(e)}")
    
    async def search_with_reranking(
        self,
        query: str,
        filter_metadata: Optional[Dict] = None,
        top_k: int = 10,
        rerank_top_k: int = 50
    ) -> List[Dict]:
        """Search with reranking for better results.
        
        Args:
            query: The search query
            filter_metadata: Optional metadata filters
            top_k: Final number of results to return
            rerank_top_k: Number of initial results to retrieve for reranking
            
        Returns:
            List of reranked matched resources with scores
        """
        # Get more results initially for reranking
        initial_results = await self.search_resources(
            query, 
            filter_metadata, 
            min(rerank_top_k, 100)  # Cap at 100 for performance
        )
        
        if not initial_results:
            return []
        
        try:
            # Simple reranking based on title/description relevance
            query_lower = query.lower()
            
            for result in initial_results:
                metadata = result.get("metadata", {})
                title = metadata.get("title", "").lower()
                description = metadata.get("description", "").lower()
                
                # Boost score if query terms appear in title or description
                title_boost = 0.2 if any(term in title for term in query_lower.split()) else 0
                desc_boost = 0.1 if any(term in description for term in query_lower.split()) else 0
                
                result["score"] = result["score"] + title_boost + desc_boost
            
            # Re-sort by adjusted score and return top_k
            initial_results.sort(key=lambda x: x["score"], reverse=True)
            return initial_results[:top_k]
            
        except Exception as e:
            logger.warning(f"Reranking failed, returning original results: {e}")
            return initial_results[:top_k]
    
    def _sanitize_metadata(self, metadata: Dict) -> Dict:
        """Sanitize metadata for Pinecone storage.
        
        Args:
            metadata: Raw metadata dictionary
            
        Returns:
            Sanitized metadata dictionary
        """
        sanitized = {}
        
        for key, value in metadata.items():
            # Skip null values
            if value is None:
                continue
            
            # Handle empty strings
            if isinstance(value, str) and value == "":
                continue
            
            # Truncate long strings
            if isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000]
            # Flatten nested dictionaries
            elif isinstance(value, dict):
                sanitized[f"{key}_flattened"] = str(value)
            # Convert lists to strings
            elif isinstance(value, list):
                sanitized[key] = ", ".join(str(item) for item in value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _validate_resource_id(self, resource_id: int) -> None:
        """Validate resource ID."""
        if not isinstance(resource_id, int) or resource_id <= 0:
            raise MetadataValidationError("Invalid resource ID")
    
    def _validate_content(self, content: str) -> None:
        """Validate content for indexing."""
        if not content or content.strip() == "":
            raise MetadataValidationError("Content cannot be empty")
        
        if len(content) > self.config.max_content_length:
            raise MetadataValidationError(f"Content too long for embedding processing (max: {self.config.max_content_length})")
    
    def _validate_query(self, query: str) -> None:
        """Validate search query."""
        if not query or query.strip() == "":
            raise SearchQueryError("Query cannot be empty")
        
        if len(query) > self.config.max_query_length:
            raise SearchQueryError(f"Query too long (max: {self.config.max_query_length})")
    
    def _validate_filter_metadata(self, filter_metadata: Dict) -> None:
        """Validate filter metadata for search operations.
        
        Args:
            filter_metadata: Filter metadata dictionary
            
        Raises:
            MetadataValidationError: If filter metadata is invalid
        """
        for key, value in filter_metadata.items():
            # Check for nested objects
            if isinstance(value, dict):
                raise MetadataValidationError("Invalid filter: nested objects not supported")
            
            # Check for lists
            if isinstance(value, list):
                raise MetadataValidationError("Invalid filter: list values not supported")
            
            # Check for null values
            if value is None:
                raise MetadataValidationError("Invalid filter: null values not supported") 
   
    def _invalidate_resource_cache(self, resource_id: int, metadata: Dict):
        """Invalidate cache entries related to a specific resource."""
        try:
            # Invalidate by resource ID
            self.search_cache.invalidate_pattern(f'"resource_id":{resource_id}')
            
            # Invalidate by metadata fields that might be used in filters
            for key, value in metadata.items():
                if key in ['category', 'project_id', 'author', 'tags']:
                    self.search_cache.invalidate_pattern(f'"{key}":"{value}"')
            
            logger.debug(f"Invalidated cache entries for resource {resource_id}")
        except Exception as e:
            logger.warning(f"Cache invalidation error for resource {resource_id}: {e}")
    
    def clear_cache(self):
        """Clear all caches."""
        self.search_cache.clear()
        self.embedding_cache.clear()
        logger.info("All caches cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            "search_cache": self.search_cache.get_stats(),
            "embedding_cache": self.embedding_cache.get_stats(),
            "metrics": self.metrics.copy()
        }
    
    def configure_cache(self, 
                       enable_search_cache: bool = True, 
                       search_cache_ttl: int = 3600,
                       enable_compression: bool = True,
                       max_search_cache_size: int = 1000,
                       max_embedding_cache_size: int = 500):
        """Configure cache settings."""
        self.search_cache.enabled = enable_search_cache
        self.search_cache.default_ttl = search_cache_ttl
        self.search_cache.use_compression = enable_compression
        self.search_cache.max_size = max_search_cache_size
        self.embedding_cache.max_size = max_embedding_cache_size
        
        logger.info(f"Cache configured: search_enabled={enable_search_cache}, "
                   f"ttl={search_cache_ttl}s, compression={enable_compression}, "
                   f"search_max_size={max_search_cache_size}, "
                   f"embedding_max_size={max_embedding_cache_size}")
    
    def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a specific user."""
        self.search_cache.invalidate_user_cache(user_id)
        logger.info(f"Invalidated cache entries for user: {user_id}")
    
    def invalidate_project_cache(self, project_id: str):
        """Invalidate all cache entries for a specific project."""
        self.search_cache.invalidate_pattern(f'"project_id":"{project_id}"')
        logger.info(f"Invalidated cache entries for project: {project_id}")
    
    async def warm_up_cache(self, common_queries: List[str], user_filters: Optional[List[Dict]] = None):
        """Warm up cache with common queries and user-specific filters."""
        logger.info(f"Warming up cache with {len(common_queries)} queries")
        
        # Default filters if none provided
        if user_filters is None:
            user_filters = [None]  # No filter
        
        total_warmed = 0
        for query in common_queries:
            for filter_metadata in user_filters:
                try:
                    await self.search_resources(query, filter_metadata=filter_metadata, top_k=5)
                    total_warmed += 1
                    logger.debug(f"Warmed up cache for query: {query[:50]}... with filter: {filter_metadata}")
                except Exception as e:
                    logger.warning(f"Failed to warm up cache for query '{query[:50]}...' with filter {filter_metadata}: {e}")
        
        logger.info(f"Cache warm-up completed: {total_warmed} entries warmed")
    
    async def warm_up_embeddings_cache(self, common_texts: List[str]):
        """Warm up embedding cache with common texts."""
        logger.info(f"Warming up embedding cache with {len(common_texts)} texts")
        
        for text in common_texts:
            try:
                self._generate_embedding_with_cache(text)
                logger.debug(f"Warmed up embedding cache for text: {text[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to warm up embedding cache for text '{text[:50]}...': {e}")
        
        logger.info("Embedding cache warm-up completed")
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get service health status."""
        try:
            # Test Pinecone connection
            index_stats = self.index.describe_index_stats()
            pinecone_healthy = True
        except Exception as e:
            logger.error(f"Pinecone health check failed: {e}")
            pinecone_healthy = False
            index_stats = None
        
        # Test cache connectivity
        cache_healthy = True
        try:
            if self.search_cache.redis_client:
                self.search_cache.redis_client.ping()
        except Exception as e:
            logger.warning(f"Cache health check failed: {e}")
            cache_healthy = False
        
        return {
            "pinecone_healthy": pinecone_healthy,
            "cache_healthy": cache_healthy,
            "index_stats": index_stats,
            "embedding_model_loaded": self.model is not None,
            "cache_stats": self.get_cache_stats(),
            "metrics": self.metrics.copy(),
            "service_status": "healthy" if (pinecone_healthy and cache_healthy) else "degraded"
        }