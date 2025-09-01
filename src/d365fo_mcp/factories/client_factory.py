"""
D365 Client Factory

Creates client instances based on configuration.
"""

from typing import Dict, Any, Optional
import structlog

from ..config import Settings
from ..auth import IAuthProvider
from ..client import ID365Client, D365Client

logger = structlog.get_logger(__name__)


class MockD365Client(ID365Client):
    """Mock D365 client for testing"""
    
    def __init__(self, auth_provider: IAuthProvider):
        self.auth_provider = auth_provider
        self.default_company = "MOCK"
    
    async def get_user_default_company(self) -> str:
        """Returns mock company"""
        return self.default_company
    
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
        """Returns mock entity data"""
        mock_records = [
            {"id": "1", "Name": f"Mock {entity_name} 1", "dataAreaId": dataareaid or self.default_company},
            {"id": "2", "Name": f"Mock {entity_name} 2", "dataAreaId": dataareaid or self.default_company},
        ]
        
        # Apply simple top filtering
        if top:
            mock_records = mock_records[:top]
            
        result = {
            "value": mock_records,
            "@odata.context": f"MockContext#{entity_name}"
        }
        
        if count:
            result["@odata.count"] = len(mock_records)
            
        return result
    
    async def create_odata_entity(
        self,
        entity_name: str,
        data: Dict[str, Any],
        dataareaid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Returns mock created record"""
        created_record = data.copy()
        created_record.update({
            "id": "mock_created_123",
            "RecId": 123456,
            "dataAreaId": dataareaid or self.default_company
        })
        return created_record
    
    async def update_odata_entity(
        self,
        entity_name: str,
        key_values: Dict[str, Any],
        data: Dict[str, Any],
        dataareaid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Returns mock updated record"""
        updated_record = data.copy()
        updated_record.update(key_values)
        updated_record["dataAreaId"] = dataareaid or self.default_company
        return updated_record
    
    async def delete_odata_entity(
        self,
        entity_name: str,
        key_values: Dict[str, Any],
        dataareaid: Optional[str] = None,
    ) -> bool:
        """Returns True for mock deletion"""
        return True
    
    async def list_odata_entities(self) -> str:
        """Returns mock metadata XML"""
        return f'''<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="4.0" xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
  <edmx:DataServices>
    <Schema Namespace="MockService" xmlns="http://docs.oasis-open.org/odata/ns/edm">
      <EntityContainer Name="Container">
        <EntitySet Name="MockEntities" EntityType="MockService.MockEntity"/>
      </EntityContainer>
      <EntityType Name="MockEntity">
        <Key>
          <PropertyRef Name="id"/>
        </Key>
        <Property Name="id" Type="Edm.String" Nullable="false"/>
        <Property Name="Name" Type="Edm.String"/>
      </EntityType>
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>'''
    
    def get_client_info(self) -> Dict[str, Any]:
        """Returns mock client info"""
        return {
            "type": "mock_client",
            "version": "1.0.0",
            "capabilities": ["get", "create", "update", "delete", "list_metadata"],
            "default_company": self.default_company
        }


class ClientFactory:
    """Factory for creating D365 clients"""
    
    @staticmethod
    async def create(settings: Settings, auth_provider: IAuthProvider) -> ID365Client:
        """
        Create D365 client based on configuration.
        
        Args:
            settings: Application settings
            auth_provider: Configured auth provider
            
        Returns:
            Configured D365 client instance
            
        Raises:
            ValueError: If client type is not supported
        """
        client_type = settings.d365_client.lower()
        
        logger.info("Creating D365 client", client_type=client_type)
        
        if client_type == "odata":
            # Get token for the OData client
            token = await auth_provider.get_token({"user_id": "system"})
            return D365Client(token, auth_provider)
        elif client_type == "mock":
            return MockD365Client(auth_provider)
        else:
            raise ValueError(f"Unsupported D365 client: {client_type}")
    
    @staticmethod
    def get_available_clients() -> list[str]:
        """Get list of available client types"""
        return ["odata", "mock"]