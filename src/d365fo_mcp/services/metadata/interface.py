"""
Metadata Service Interface

Defines contract for metadata service implementations
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IMetadataService(ABC):
    """Interface for metadata services"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the metadata service"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close service connections and cleanup"""
        pass
    
    # Entity discovery
    @abstractmethod
    async def search_entities(self, pattern: str, limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
        """
        Search for entities by name pattern.
        
        Args:
            pattern: Search term
            limit: Maximum results
            skip: Results to skip
            
        Returns:
            List of matching entities with metadata
        """
        pass
    
    @abstractmethod
    async def list_all_entities(self) -> List[Dict[str, Any]]:
        """
        List all available entities.
        
        Returns:
            Complete entity inventory
        """
        pass
    
    # Entity metadata
    @abstractmethod
    async def get_entity_metadata(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive metadata for specific entity.
        
        Args:
            entity_name: Target entity name
            
        Returns:
            Complete entity metadata or None if not found
        """
        pass
    
    @abstractmethod
    async def get_entity_fields(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Get field definitions for entity.
        
        Args:
            entity_name: Target entity name
            
        Returns:
            List of field definitions
        """
        pass
    
    # Cache management
    @abstractmethod
    async def refresh_metadata_cache(self, force: bool = False) -> Dict[str, Any]:
        """
        Refresh metadata cache from D365.
        
        Args:
            force: Force refresh even if cache is valid
            
        Returns:
            Refresh operation results
        """
        pass
    
    @abstractmethod
    async def clear_metadata_cache(self) -> None:
        """Clear all metadata cache"""
        pass
    
    @abstractmethod
    async def get_cache_status(self) -> Dict[str, Any]:
        """
        Get metadata cache status.
        
        Returns:
            Cache status information
        """
        pass
    
    # Enum operations
    @abstractmethod
    async def search_enums(self, pattern: str, limit: int = 20, skip: int = 0) -> Dict[str, Any]:
        """
        Search for enums by name pattern.
        
        Args:
            pattern: Search term
            limit: Maximum results
            skip: Results to skip
            
        Returns:
            Search results with pagination
        """
        pass
    
    @abstractmethod
    async def get_enum_metadata(self, enum_name: str) -> Optional[Dict[str, Any]]:
        """
        Get enum definition with all valid values.
        
        Args:
            enum_name: Target enum name
            
        Returns:
            Complete enum metadata or None if not found
        """
        pass
    
    @abstractmethod
    async def get_entity_enum_fields(self, entity_name: str) -> Dict[str, Any]:
        """
        Get all enum fields for a specific entity.
        
        Args:
            entity_name: Target entity name
            
        Returns:
            Mapping of field names to enum types
        """
        pass
    
    # Performance and diagnostics
    @abstractmethod
    async def ensure_metadata_available(self, timeout_seconds: int = 60) -> bool:
        """
        Ensure metadata is available, waiting if necessary.
        
        Args:
            timeout_seconds: Maximum wait time
            
        Returns:
            True if metadata available, False if timeout
        """
        pass
    
    @abstractmethod
    async def get_metadata_stats(self) -> Dict[str, Any]:
        """
        Get metadata cache statistics and performance information.
        
        Returns:
            Statistics about cache performance
        """
        pass
    
    # Service info
    @abstractmethod
    async def get_service_info(self) -> Dict[str, Any]:
        """
        Get service implementation information.
        
        Returns:
            Service metadata (type, capabilities, stats, etc.)
        """
        pass