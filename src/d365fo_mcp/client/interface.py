"""
D365 Client Interface

Defines contract for D365 Finance & Operations clients
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Literal


CompanyMode = Literal["default", "specific", "all", "auto"]


class ID365Client(ABC):
    """Interface for D365 Finance & Operations clients"""
    
    @abstractmethod
    async def get_user_default_company(self) -> str:
        """
        Get the user's default company code.
        
        Returns:
            Default company code (e.g., 'USMF')
        """
        pass
    
    @abstractmethod
    async def get_odata_entity(
        self,
        entity_name: str,
        filter_query: Optional[str] = None,
        select_fields: Optional[str] = None,
        top: Optional[int] = None,
        skip: Optional[int] = None,
        orderby: Optional[str] = None,
        count: bool = False,
        dataareaid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute OData GET query against D365 entity.
        
        Args:
            entity_name: D365 entity name
            filter_query: OData filter expression
            select_fields: Comma-separated field names
            top: Maximum records to return
            skip: Records to skip (for pagination)
            orderby: Sort expression
            count: Include total count in response
            dataareaid: Company code filter
            
        Returns:
            OData response with entity data
        """
        pass
    
    @abstractmethod
    async def create_odata_entity(
        self,
        entity_name: str,
        data: Dict[str, Any],
        dataareaid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create new entity record via OData POST.
        
        Args:
            entity_name: Target entity name
            data: Record data
            dataareaid: Company code
            
        Returns:
            Created record with system-generated fields
        """
        pass
    
    @abstractmethod
    async def update_odata_entity(
        self,
        entity_name: str,
        key_values: Dict[str, Any],
        data: Dict[str, Any],
        dataareaid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update existing entity record via OData PATCH.
        
        Args:
            entity_name: Target entity name
            key_values: Key field values to identify record
            data: Fields to update
            dataareaid: Company code
            
        Returns:
            Updated record data
        """
        pass
    
    @abstractmethod
    async def delete_odata_entity(
        self,
        entity_name: str,
        key_values: Dict[str, Any],
        dataareaid: Optional[str] = None,
    ) -> bool:
        """
        Delete entity record via OData DELETE.
        
        Args:
            entity_name: Target entity name
            key_values: Key field values to identify record
            dataareaid: Company code
            
        Returns:
            True if deletion successful
        """
        pass
    
    @abstractmethod
    async def list_odata_entities(self) -> str:
        """
        Get raw OData metadata XML.
        
        Returns:
            Complete OData metadata document
        """
        pass
    
    @abstractmethod
    def get_client_info(self) -> Dict[str, Any]:
        """
        Get client implementation information.
        
        Returns:
            Client metadata (type, version, capabilities, etc.)
        """
        pass