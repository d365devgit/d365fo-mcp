"""
Instructions Service Interface

Defines contract for instructions service implementations
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IInstructionsService(ABC):
    """Interface for instructions services"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the instructions service"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close service connections and cleanup"""
        pass
    
    # Instruction management
    @abstractmethod
    async def save_or_update_instruction(
        self,
        entity_name: str,
        operation_type: str,
        instruction: Dict[str, Any],
        update_mode: str = "merge"
    ) -> str:
        """
        Save or intelligently update instruction.
        
        Args:
            entity_name: Target entity name
            operation_type: Operation type (read, create, update, delete)
            instruction: Instruction data
            update_mode: How to handle existing (merge, replace, append)
            
        Returns:
            Instruction ID
        """
        pass
    
    @abstractmethod
    async def get_entity_instructions(
        self,
        entity_name: str,
        operation_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get instructions for entity and operation.
        
        Args:
            entity_name: Target entity name
            operation_type: Operation type filter
            
        Returns:
            Instructions with metadata and analytics
        """
        pass
    
    @abstractmethod
    async def search_instructions(
        self,
        query: str,
        operation_type: Optional[str] = None,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search instructions by content.
        
        Args:
            query: Search query
            operation_type: Operation type filter
            limit: Maximum results
            skip: Results to skip
            
        Returns:
            Matching instructions
        """
        pass
    
    @abstractmethod
    async def rate_instruction_success(
        self,
        instruction_id: str,
        success: bool,
        feedback_score: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Rate instruction success/failure.
        
        Args:
            instruction_id: Instruction ID to rate
            success: Whether instruction was successful
            feedback_score: User feedback score (1-5)
            metadata: Additional feedback metadata
        """
        pass
    
    @abstractmethod
    async def get_instruction_analytics(
        self,
        entity_name: Optional[str] = None,
        operation_type: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get instruction usage analytics.
        
        Args:
            entity_name: Filter by entity
            operation_type: Filter by operation
            hours: Hours of history to analyze
            
        Returns:
            Usage analytics and success rates
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