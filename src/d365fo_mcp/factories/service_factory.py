"""
Service Factory

Creates service instances using repository dependencies.
"""

import structlog
from typing import Optional

from ..services.metadata import IMetadataService, MetadataService, BackgroundMetadataSync
from ..services.instructions import IInstructionsService, InstructionsService
from ..repositories.metadata import IMetadataRepository
from ..repositories.instructions import IInstructionsRepository
from ..client import ID365Client
from ..repositories.sqlite.database import Database

logger = structlog.get_logger(__name__)


class ServiceFactory:
    """Factory for creating service instances with proper dependency injection"""
    
    @staticmethod
    def create_metadata_service(
        metadata_repository: IMetadataRepository,
        d365_client: ID365Client,
        enable_background_sync: bool = False,
        database: Optional[Database] = None
    ) -> IMetadataService:
        """
        Create metadata service with repository dependency.
        
        Args:
            metadata_repository: Initialized metadata repository
            d365_client: Initialized D365 client
            enable_background_sync: Whether to enable background metadata synchronization
            database: Database instance (required if background sync enabled)
            
        Returns:
            Configured metadata service instance
        """
        logger.info("Creating metadata service", background_sync=enable_background_sync)
        
        background_sync = None
        if enable_background_sync and database:
            logger.info("Enabling background metadata sync")
            background_sync = BackgroundMetadataSync(database, d365_client)
        
        return MetadataService(metadata_repository, d365_client, background_sync)
    
    @staticmethod
    def create_instructions_service(
        instructions_repository: IInstructionsRepository
    ) -> IInstructionsService:
        """
        Create instructions service with repository dependency.
        
        Args:
            instructions_repository: Initialized instructions repository
            
        Returns:
            Configured instructions service instance
        """
        logger.info("Creating instructions service")
        return InstructionsService(instructions_repository)