"""
Metadata Service Implementation

Business logic layer for metadata operations using repository pattern.
Enhanced with background sync capabilities.
"""

from typing import Dict, Any, List, Optional
import structlog
import time

from .interface import IMetadataService
from ...repositories.metadata import IMetadataRepository
from ...client import ID365Client
from .background_sync import BackgroundMetadataSync

logger = structlog.get_logger(__name__)


class MetadataService(IMetadataService):
    """Metadata service implementation using repository pattern with background sync"""
    
    def __init__(
        self, 
        metadata_repository: IMetadataRepository, 
        d365_client: ID365Client,
        background_sync: Optional[BackgroundMetadataSync] = None
    ):
        self.repository = metadata_repository
        self.client = d365_client
        self.background_sync = background_sync
        self._initialized = False
        
        # Performance counters
        self._query_stats = {
            "entity_searches": 0,
            "metadata_lookups": 0, 
            "enum_searches": 0,
            "cache_hits": 0,
            "total_query_time_ms": 0
        }
    
    async def initialize(self) -> None:
        """Initialize the metadata service"""
        if not self._initialized:
            await self.repository.initialize()
            
            # Start background sync if configured
            if self.background_sync:
                await self.background_sync.start_background_sync()
                logger.info("Background metadata sync started")
            
            self._initialized = True
            logger.info("Metadata service initialized")
    
    async def close(self) -> None:
        """Close service connections and cleanup"""
        if self.background_sync:
            await self.background_sync.stop_background_sync()
            
        await self.repository.close()
        logger.info("Metadata service closed")
    
    # Entity discovery
    async def search_entities(self, pattern: str, limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
        """Search for entities by name pattern"""
        await self._ensure_initialized()
        
        logger.info("Searching entities", pattern=pattern, limit=limit, skip=skip)
        
        # Record usage stats
        await self.repository.record_usage_stat("search_entities", metadata={"pattern": pattern})
        
        # Repository now returns Dict with structured results, extract the entities list
        search_results = await self.repository.search_entities(pattern, limit, skip)
        
        if isinstance(search_results, dict):
            # Return the detailed entities from the structured response
            return search_results.get("detailed_entities", search_results.get("entities", []))
        else:
            # Fallback for repositories that still return lists
            return search_results
    
    async def list_all_entities(self) -> List[Dict[str, Any]]:
        """List all available entities"""
        await self._ensure_initialized()
        
        logger.info("Listing all entities")
        
        # Record usage stats
        await self.repository.record_usage_stat("list_all_entities")
        
        return await self.repository.list_cached_entities()
    
    # Entity metadata
    async def get_entity_metadata(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive metadata for specific entity"""
        await self._ensure_initialized()
        
        logger.info("Getting entity metadata", entity_name=entity_name)
        
        # Try to get from cache first
        metadata = await self.repository.get_cached_entity_metadata(entity_name)
        
        if metadata:
            await self.repository.record_usage_stat("get_entity_metadata", entity_name, True)
            return metadata
        
        # If not cached, we don't have it (cache should be populated by background sync)
        await self.repository.record_usage_stat("get_entity_metadata", entity_name, False)
        logger.warning("Entity metadata not found in cache", entity_name=entity_name)
        
        return None
    
    async def get_entity_fields(self, entity_name: str) -> List[Dict[str, Any]]:
        """Get field definitions for entity"""
        await self._ensure_initialized()
        
        logger.info("Getting entity fields", entity_name=entity_name)
        
        # Get full metadata and extract fields
        metadata = await self.get_entity_metadata(entity_name)
        
        if metadata and "fields" in metadata:
            return metadata["fields"]
        
        return []
    
    # Cache management
    async def refresh_metadata_cache(self, force: bool = False) -> Dict[str, Any]:
        """Refresh metadata cache from D365"""
        await self._ensure_initialized()
        
        logger.info("Refreshing metadata cache", force=force)
        
        # Check if cache is valid and force is not requested
        if not force and await self.repository.is_metadata_cache_valid():
            return {"status": "cache_valid", "refreshed": False}
        
        try:
            # Fetch fresh metadata from D365
            raw_metadata = await self.client.list_odata_entities()
            
            # Cache the raw metadata
            await self.repository.cache_raw_metadata(raw_metadata)
            
            # TODO: Parse and cache individual entity metadata
            # This would involve parsing the XML and extracting entity definitions
            # For now, we just cache the raw metadata
            
            await self.repository.record_usage_stat("refresh_metadata_cache", success=True)
            
            return {
                "status": "refreshed",
                "refreshed": True,
                "metadata_size_bytes": len(raw_metadata)
            }
            
        except Exception as e:
            logger.error("Failed to refresh metadata cache", error=str(e))
            await self.repository.record_usage_stat("refresh_metadata_cache", success=False)
            
            return {
                "status": "error",
                "refreshed": False,
                "error": str(e)
            }
    
    async def get_cache_status(self) -> Dict[str, Any]:
        """Get metadata cache status"""
        await self._ensure_initialized()
        
        is_valid = await self.repository.is_metadata_cache_valid()
        cached_entities = await self.repository.list_cached_entities()
        
        return {
            "cache_valid": is_valid,
            "cached_entities_count": len(cached_entities),
            "repository_info": await self.repository.get_repository_info()
        }
    
    # Service info
    async def get_service_info(self) -> Dict[str, Any]:
        """Get service implementation information"""
        repo_info = await self.repository.get_repository_info()
        client_info = self.client.get_client_info()
        
        return {
            "type": "metadata_service",
            "version": "1.0.0",
            "initialized": self._initialized,
            "background_sync_enabled": self.background_sync is not None,
            "repository": repo_info,
            "client": client_info,
            "capabilities": [
                "entity_search",
                "metadata_retrieval",
                "cache_management",
                "usage_analytics",
                "enum_operations",
                "background_sync"
            ]
        }
    
    # Enum operations (delegated to repository)
    async def search_enums(self, pattern: str, limit: int = 20, skip: int = 0) -> Dict[str, Any]:
        """Search for enums by name pattern"""
        await self._ensure_initialized()
        
        start_time = time.time()
        logger.info("Searching enums", pattern=pattern, limit=limit, skip=skip)
        
        try:
            results = await self.repository.search_enums(pattern, limit, skip)
            
            # Update stats
            self._query_stats["enum_searches"] += 1
            self._query_stats["total_query_time_ms"] += int((time.time() - start_time) * 1000)
            
            await self.repository.record_usage_stat("search_enums", metadata={"pattern": pattern})
            
            return {
                "enums": results,
                "pagination_info": {
                    "current_page": skip // limit + 1 if limit > 0 else 1,
                    "page_size": limit,
                    "total_results": len(results),
                    "has_more": len(results) == limit
                }
            }
            
        except Exception as e:
            logger.error("Failed to search enums", error=str(e))
            await self.repository.record_usage_stat("search_enums", success=False)
            raise
    
    async def get_enum_metadata(self, enum_name: str) -> Optional[Dict[str, Any]]:
        """Get enum definition with all valid values"""
        await self._ensure_initialized()
        
        logger.info("Getting enum metadata", enum_name=enum_name)
        
        try:
            result = await self.repository.get_enum_metadata(enum_name)
            
            # Update stats
            self._query_stats["metadata_lookups"] += 1
            await self.repository.record_usage_stat("get_enum_metadata", entity_name=enum_name)
            
            return result
            
        except Exception as e:
            logger.error("Failed to get enum metadata", enum_name=enum_name, error=str(e))
            await self.repository.record_usage_stat("get_enum_metadata", entity_name=enum_name, success=False)
            raise
    
    async def get_entity_enum_fields(self, entity_name: str) -> Dict[str, Any]:
        """Get all enum fields for a specific entity"""
        await self._ensure_initialized()
        
        logger.info("Getting entity enum fields", entity_name=entity_name)
        
        try:
            result = await self.repository.get_entity_enum_fields(entity_name)
            
            await self.repository.record_usage_stat("get_entity_enum_fields", entity_name=entity_name)
            
            return result
            
        except Exception as e:
            logger.error("Failed to get entity enum fields", entity_name=entity_name, error=str(e))
            await self.repository.record_usage_stat("get_entity_enum_fields", entity_name=entity_name, success=False)
            raise
    
    # Performance and diagnostics
    async def ensure_metadata_available(self, timeout_seconds: int = 60) -> bool:
        """Ensure metadata is available, waiting if necessary"""
        await self._ensure_initialized()
        
        logger.info("Ensuring metadata available", timeout_seconds=timeout_seconds)
        
        # Check if we have cached metadata
        is_valid = await self.repository.is_metadata_cache_valid()
        if is_valid:
            return True
        
        # If background sync is enabled, check sync status and wait if needed
        if self.background_sync:
            status = await self.background_sync.get_sync_status()
            if status.get("metadata_available", False):
                return True
            
            # Trigger sync and wait with timeout
            await self.background_sync.force_sync_now()
            
            # Simple timeout waiting
            import asyncio
            start_time = time.time()
            while time.time() - start_time < timeout_seconds:
                if await self.repository.is_metadata_cache_valid():
                    return True
                await asyncio.sleep(1)
            
            return False
        
        # Otherwise, try to refresh synchronously
        try:
            result = await self.refresh_metadata_cache(force=True)
            return result.get("refreshed", False)
        except Exception:
            return False
    
    async def get_metadata_stats(self) -> Dict[str, Any]:
        """Get metadata cache statistics and performance information"""
        await self._ensure_initialized()
        
        cache_status = await self.get_cache_status()
        
        sync_status = None
        if self.background_sync:
            sync_status = await self.background_sync.get_sync_status()
        
        return {
            "query_statistics": self._query_stats.copy(),
            "cache_status": cache_status,
            "background_sync_status": sync_status or {"enabled": False}
        }
    
    async def clear_metadata_cache(self) -> None:
        """Clear all metadata cache"""
        await self._ensure_initialized()
        
        logger.info("Clearing metadata cache")
        
        try:
            await self.repository.clear_metadata_cache()
            
            # Reset query stats
            self._query_stats = {
                "entity_searches": 0,
                "metadata_lookups": 0, 
                "enum_searches": 0,
                "cache_hits": 0,
                "total_query_time_ms": 0
            }
            
            await self.repository.record_usage_stat("clear_metadata_cache")
            
        except Exception as e:
            logger.error("Failed to clear metadata cache", error=str(e))
            await self.repository.record_usage_stat("clear_metadata_cache", success=False)
            raise
    
    # Private methods
    async def _ensure_initialized(self) -> None:
        """Ensure service is initialized"""
        if not self._initialized:
            await self.initialize()