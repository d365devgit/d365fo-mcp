"""
Instructions Repository Interface

Defines contract for instructions storage providers (SQLite, Supabase, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IInstructionsRepository(ABC):
    """Interface for instructions storage repositories"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the repository (create tables, connections, etc.)"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close repository connections and cleanup"""
        pass
    
    # Instruction operations
    @abstractmethod
    async def save_instruction(
        self,
        entity_name: str,
        operation_type: str,
        instruction: Dict[str, Any]
    ) -> str:
        """
        Save a new instruction.
        
        Args:
            entity_name: Target entity name
            operation_type: Operation type (read, create, update, delete)
            instruction: Instruction data
            
        Returns:
            Instruction ID
        """
        pass
    
    @abstractmethod
    async def update_instruction(
        self,
        instruction_id: str,
        instruction: Dict[str, Any]
    ) -> None:
        """
        Update an existing instruction.
        
        Args:
            instruction_id: Instruction ID to update
            instruction: Updated instruction data
        """
        pass
    
    @abstractmethod
    async def get_instruction(self, instruction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get instruction by ID.
        
        Args:
            instruction_id: Instruction ID
            
        Returns:
            Instruction data or None if not found
        """
        pass
    
    @abstractmethod
    async def get_entity_instructions(
        self,
        entity_name: str,
        operation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get instructions for an entity and operation.
        
        Args:
            entity_name: Target entity name
            operation_type: Operation type filter (optional)
            
        Returns:
            List of matching instructions
        """
        pass
    
    @abstractmethod
    async def search_instructions(
        self,
        query: str,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search instructions by content.
        
        Args:
            query: Search query
            limit: Maximum results
            skip: Results to skip
            
        Returns:
            Matching instructions
        """
        pass
    
    @abstractmethod
    async def delete_instruction(self, instruction_id: str) -> bool:
        """
        Delete an instruction.
        
        Args:
            instruction_id: Instruction ID to delete
            
        Returns:
            True if deletion successful
        """
        pass
    
    # Statistics and analytics
    @abstractmethod
    async def record_instruction_usage(
        self,
        instruction_id: str,
        success: bool = True,
        feedback_score: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record instruction usage statistics.
        
        Args:
            instruction_id: Instruction ID used
            success: Whether instruction led to success
            feedback_score: User feedback score (1-5)
            metadata: Additional usage metadata
        """
        pass
    
    @abstractmethod
    async def get_instruction_stats(
        self,
        instruction_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get instruction usage statistics.
        
        Args:
            instruction_id: Filter by instruction ID
            entity_name: Filter by entity name
            hours: Hours of history to include
            
        Returns:
            Usage statistics and success rates
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