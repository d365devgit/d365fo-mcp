"""
Metadata Repository Interface

Defines contract for metadata storage providers (SQLite, Supabase, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IMetadataRepository(ABC):
    """Interface for metadata storage repositories"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the repository (create tables, connections, etc.)"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close repository connections and cleanup"""
        pass
    
    # Entity metadata operations
    @abstractmethod
    async def cache_entity_metadata(self, entity_name: str, metadata: Dict[str, Any]) -> None:
        """
        Cache entity metadata for fast retrieval.
        
        Args:
            entity_name: Entity name
            metadata: Complete entity metadata structure
        """
        pass
    
    @abstractmethod
    async def get_cached_entity_metadata(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached entity metadata.
        
        Args:
            entity_name: Entity name
            
        Returns:
            Cached metadata or None if not found
        """
        pass
    
    @abstractmethod
    async def list_cached_entities(self) -> List[Dict[str, Any]]:
        """
        List all cached entities with basic metadata.
        
        Returns:
            List of entity summaries
        """
        pass
    
    @abstractmethod
    async def search_entities(self, pattern: str, limit: int = 20, skip: int = 0) -> Dict[str, Any]:
        """
        Search entities by name pattern.
        
        Args:
            pattern: Search pattern
            limit: Maximum results
            skip: Results to skip
            
        Returns:
            Search results with pagination info and entity list
        """
        pass
    
    # Raw metadata operations
    @abstractmethod
    async def cache_raw_metadata(self, metadata_xml: str) -> None:
        """
        Cache raw OData metadata XML.
        
        Args:
            metadata_xml: Complete metadata XML
        """
        pass
    
    @abstractmethod
    async def get_cached_raw_metadata(self) -> Optional[str]:
        """
        Retrieve cached raw metadata XML.
        
        Returns:
            Cached XML or None if not found/expired
        """
        pass
    
    @abstractmethod
    async def is_metadata_cache_valid(self) -> bool:
        """
        Check if metadata cache is still valid (not expired).
        
        Returns:
            True if cache is valid
        """
        pass
    
    # Enum operations
    @abstractmethod
    async def search_enums(self, pattern: str, limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
        """
        Search for enums by name pattern.
        
        Args:
            pattern: Search term
            limit: Maximum results
            skip: Results to skip
            
        Returns:
            List of matching enums
        """
        pass
    
    @abstractmethod
    async def get_enum_metadata(self, enum_name: str) -> Optional[Dict[str, Any]]:
        """
        Get enum metadata with all values.
        
        Args:
            enum_name: Target enum name
            
        Returns:
            Enum metadata or None if not found
        """
        pass
    
    @abstractmethod
    async def get_entity_enum_fields(self, entity_name: str) -> Dict[str, Any]:
        """
        Get all enum fields for an entity.
        
        Args:
            entity_name: Target entity name
            
        Returns:
            Mapping of field names to enum types
        """
        pass
    
    @abstractmethod
    async def clear_metadata_cache(self) -> None:
        """Clear all metadata cache"""
        pass
    
    # Statistics operations
    @abstractmethod
    async def record_usage_stat(
        self,
        operation: str,
        entity_name: Optional[str] = None,
        success: bool = True,
        execution_time_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record usage statistics.
        
        Args:
            operation: Operation type (search, get_metadata, query, etc.)
            entity_name: Target entity (if applicable)
            success: Whether operation succeeded
            execution_time_ms: Execution time in milliseconds
            metadata: Additional metadata
        """
        pass
    
    @abstractmethod
    async def get_usage_stats(
        self,
        operation: Optional[str] = None,
        entity_name: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get usage statistics.
        
        Args:
            operation: Filter by operation type
            entity_name: Filter by entity name
            hours: Hours of history to include
            
        Returns:
            Usage statistics
        """
        pass
    
    @abstractmethod
    async def get_repository_info(self) -> Dict[str, Any]:
        """
        Get repository implementation information.
        
        Returns:
            Repository metadata (type, connection info, stats, etc.)
        """
        pass