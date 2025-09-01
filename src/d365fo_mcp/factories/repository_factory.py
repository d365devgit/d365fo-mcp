"""
Repository Factory

Creates repository instances based on configuration.
"""

from typing import Union
from pathlib import Path
import structlog

from ..config import Settings
from ..repositories.metadata import IMetadataRepository
from ..repositories.instructions import IInstructionsRepository
from ..repositories.sqlite import SQLiteMetadataRepository, SQLiteInstructionsRepository

logger = structlog.get_logger(__name__)


class RepositoryFactory:
    """Factory for creating repository instances"""
    
    @staticmethod
    def create_metadata_repository(settings: Settings) -> IMetadataRepository:
        """
        Create metadata repository based on configuration.
        
        Args:
            settings: Application settings
            
        Returns:
            Configured metadata repository instance
            
        Raises:
            ValueError: If repository type is not supported
        """
        repo_type = settings.metadata_repository.lower()
        
        logger.info("Creating metadata repository", repository_type=repo_type)
        
        if repo_type == "sqlite":
            return SQLiteMetadataRepository(settings.database_path_resolved)
        elif repo_type == "supabase":
            # TODO: Implement SupabaseMetadataRepository
            # if not settings.supabase_url or not settings.supabase_key:
            #     raise ValueError("Supabase configuration missing (supabase_url, supabase_key)")
            # return SupabaseMetadataRepository(settings.supabase_url, settings.supabase_key)
            raise NotImplementedError("Supabase metadata repository not yet implemented")
        else:
            raise ValueError(f"Unsupported metadata repository: {repo_type}")
    
    @staticmethod
    def create_instructions_repository(settings: Settings) -> IInstructionsRepository:
        """
        Create instructions repository based on configuration.
        
        Args:
            settings: Application settings
            
        Returns:
            Configured instructions repository instance
            
        Raises:
            ValueError: If repository type is not supported
        """
        repo_type = settings.instructions_repository.lower()
        
        logger.info("Creating instructions repository", repository_type=repo_type)
        
        if repo_type == "sqlite":
            return SQLiteInstructionsRepository(settings.database_path_resolved)
        elif repo_type == "supabase":
            # TODO: Implement SupabaseInstructionsRepository
            # if not settings.supabase_url or not settings.supabase_key:
            #     raise ValueError("Supabase configuration missing (supabase_url, supabase_key)")
            # return SupabaseInstructionsRepository(settings.supabase_url, settings.supabase_key)
            raise NotImplementedError("Supabase instructions repository not yet implemented")
        else:
            raise ValueError(f"Unsupported instructions repository: {repo_type}")
    
    @staticmethod
    def get_available_repositories() -> dict[str, list[str]]:
        """Get list of available repository types"""
        return {
            "metadata": ["sqlite", "supabase"],
            "instructions": ["sqlite", "supabase"]
        }