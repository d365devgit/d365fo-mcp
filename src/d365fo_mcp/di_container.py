"""
Dependency Injection Container

Centralized dependency resolution for clean separation of concerns.
"""

from typing import Dict, Any, Optional
import structlog

from .config import Settings, get_settings
from .factories import AuthProviderFactory, ClientFactory, RepositoryFactory, ServiceFactory
from .services.metadata import IMetadataService
from .services.instructions import IInstructionsService
from .auth.interface import IAuthProvider
from .client.interface import ID365Client
from .repositories.metadata import IMetadataRepository
from .repositories.instructions import IInstructionsRepository
from .repositories.sqlite.database import Database

logger = structlog.get_logger(__name__)


class DIContainer:
    """
    Dependency Injection Container for managing service dependencies.
    
    Provides lazy initialization and caching of dependencies with proper
    lifecycle management and separation of concerns.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._services: Dict[str, Any] = {}
        self._initialized = False
        
        logger.info("DI Container initialized", 
                   auth_provider=self.settings.auth_provider,
                   d365_client=self.settings.d365_client,
                   metadata_repo=self.settings.metadata_repository,
                   instructions_repo=self.settings.instructions_repository)
    
    async def initialize(self) -> None:
        """Initialize all async dependencies"""
        if self._initialized:
            return
        
        # Initialize repositories first (they create database schemas)
        await self.get_metadata_repository()
        await self.get_instructions_repository()
        
        self._initialized = True
        logger.info("DI Container fully initialized")
    
    async def close(self) -> None:
        """Clean up all dependencies"""
        # Close services
        if 'metadata_service' in self._services:
            await self._services['metadata_service'].close()
        if 'instructions_service' in self._services:
            await self._services['instructions_service'].close()
        
        # Close repositories
        if 'metadata_repository' in self._services:
            await self._services['metadata_repository'].close()
        if 'instructions_repository' in self._services:
            await self._services['instructions_repository'].close()
        
        # Close database
        if 'database' in self._services:
            await self._services['database'].close()
        
        logger.info("DI Container closed")
    
    # Core Dependencies
    def get_database(self) -> Database:
        """Get database instance (lazy initialization)"""
        if 'database' not in self._services:
            self._services['database'] = Database(self.settings.database_path_resolved)
            logger.debug("Database instance created")
        return self._services['database']
    
    def get_auth_provider(self) -> IAuthProvider:
        """Get auth provider instance (lazy initialization)"""
        if 'auth_provider' not in self._services:
            self._services['auth_provider'] = AuthProviderFactory.create(self.settings)
            logger.debug("Auth provider created", type=self.settings.auth_provider)
        return self._services['auth_provider']
    
    async def get_d365_client(self) -> ID365Client:
        """Get D365 client instance (lazy initialization)"""
        if 'd365_client' not in self._services:
            auth_provider = self.get_auth_provider()
            self._services['d365_client'] = await ClientFactory.create(self.settings, auth_provider)
            logger.debug("D365 client created", type=self.settings.d365_client)
        return self._services['d365_client']
    
    # Repositories
    async def get_metadata_repository(self) -> IMetadataRepository:
        """Get metadata repository instance (lazy initialization)"""
        if 'metadata_repository' not in self._services:
            repository = RepositoryFactory.create_metadata_repository(self.settings)
            await repository.initialize()
            self._services['metadata_repository'] = repository
            logger.debug("Metadata repository created and initialized")
        return self._services['metadata_repository']
    
    async def get_instructions_repository(self) -> IInstructionsRepository:
        """Get instructions repository instance (lazy initialization)"""
        if 'instructions_repository' not in self._services:
            repository = RepositoryFactory.create_instructions_repository(self.settings)
            await repository.initialize()
            self._services['instructions_repository'] = repository
            logger.debug("Instructions repository created and initialized")
        return self._services['instructions_repository']
    
    # Services
    async def get_metadata_service(self, enable_background_sync: bool = False) -> IMetadataService:
        """Get metadata service instance (lazy initialization)"""
        if 'metadata_service' not in self._services:
            metadata_repository = await self.get_metadata_repository()
            d365_client = await self.get_d365_client()
            
            # Optionally enable background sync
            database = self.get_database() if enable_background_sync else None
            
            service = ServiceFactory.create_metadata_service(
                metadata_repository=metadata_repository,
                d365_client=d365_client,
                enable_background_sync=enable_background_sync,
                database=database
            )
            await service.initialize()
            self._services['metadata_service'] = service
            logger.debug("Metadata service created and initialized", 
                        background_sync=enable_background_sync)
        return self._services['metadata_service']
    
    async def get_instructions_service(self) -> IInstructionsService:
        """Get instructions service instance (lazy initialization)"""
        if 'instructions_service' not in self._services:
            instructions_repository = await self.get_instructions_repository()
            service = ServiceFactory.create_instructions_service(instructions_repository)
            await service.initialize()
            self._services['instructions_service'] = service
            logger.debug("Instructions service created and initialized")
        return self._services['instructions_service']
    
    # Service Info
    def get_container_info(self) -> Dict[str, Any]:
        """Get container status and dependency information"""
        return {
            "initialized": self._initialized,
            "cached_services": list(self._services.keys()),
            "settings": {
                "auth_provider": self.settings.auth_provider,
                "d365_client": self.settings.d365_client,
                "metadata_repository": self.settings.metadata_repository,
                "instructions_repository": self.settings.instructions_repository,
                "database_path": str(self.settings.database_path_resolved)
            }
        }
