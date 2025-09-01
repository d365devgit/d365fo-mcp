"""
Instructions Service Implementation

Business logic layer for instructions operations using repository pattern.
"""

from typing import Dict, Any, List, Optional
import structlog

from .interface import IInstructionsService
from ...repositories.instructions import IInstructionsRepository

logger = structlog.get_logger(__name__)


class InstructionsService(IInstructionsService):
    """Instructions service implementation using repository pattern"""
    
    def __init__(self, instructions_repository: IInstructionsRepository):
        self.repository = instructions_repository
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the instructions service"""
        if not self._initialized:
            await self.repository.initialize()
            self._initialized = True
            logger.info("Instructions service initialized")
    
    async def close(self) -> None:
        """Close service connections and cleanup"""
        await self.repository.close()
        logger.info("Instructions service closed")
    
    # Instruction management
    async def save_or_update_instruction(
        self,
        entity_name: str,
        operation_type: str,
        instruction: Dict[str, Any],
        update_mode: str = "merge"
    ) -> str:
        """Save or intelligently update instruction"""
        await self._ensure_initialized()
        
        logger.info("Saving instruction", entity_name=entity_name, operation_type=operation_type, update_mode=update_mode)
        
        # Check if instruction already exists for this entity/operation
        existing_instructions = await self.repository.get_entity_instructions(entity_name, operation_type)
        
        if existing_instructions and update_mode in ["merge", "replace"]:
            # Update existing instruction
            existing_instruction = existing_instructions[0]  # Take the first one
            instruction_id = existing_instruction["id"]
            
            if update_mode == "merge":
                # Merge with existing instruction
                merged_instruction = self._merge_instructions(existing_instruction["instruction"], instruction)
                await self.repository.update_instruction(instruction_id, merged_instruction)
            else:  # replace
                await self.repository.update_instruction(instruction_id, instruction)
            
            logger.info("Updated existing instruction", instruction_id=instruction_id, entity_name=entity_name)
            return instruction_id
            
        else:
            # Create new instruction
            instruction_id = await self.repository.save_instruction(entity_name, operation_type, instruction)
            logger.info("Created new instruction", instruction_id=instruction_id, entity_name=entity_name)
            return instruction_id
    
    async def get_entity_instructions(
        self,
        entity_name: str,
        operation_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get instructions for entity and operation"""
        await self._ensure_initialized()
        
        logger.info("Getting entity instructions", entity_name=entity_name, operation_type=operation_type)
        
        instructions = await self.repository.get_entity_instructions(entity_name, operation_type)
        
        # Get usage statistics
        stats = await self.repository.get_instruction_stats(entity_name=entity_name)
        
        # Build response with analytics
        response = {
            "entity_name": entity_name,
            "operation_type": operation_type,
            "instructions": instructions,
            "count": len(instructions),
            "statistics": stats
        }
        
        # Add success patterns and suggestions based on existing instructions
        if instructions:
            response["common_patterns"] = self._extract_common_patterns(instructions)
            response["suggestions"] = self._generate_suggestions(instructions)
        else:
            response["suggestions"] = [
                f"No instructions found for {entity_name}",
                f"Consider using get_entity_metadata('{entity_name}') first",
                "Start with simple queries before adding complexity"
            ]
        
        return response
    
    async def search_instructions(
        self,
        query: str,
        operation_type: Optional[str] = None,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Search instructions by content"""
        await self._ensure_initialized()
        
        logger.info("Searching instructions", query=query, operation_type=operation_type)
        
        # Repository search doesn't filter by operation_type yet, so we do it here
        all_results = await self.repository.search_instructions(query, limit, skip)
        
        if operation_type:
            filtered_results = [inst for inst in all_results if inst.get("operation_type") == operation_type]
            return filtered_results
        
        return all_results
    
    async def rate_instruction_success(
        self,
        instruction_id: str,
        success: bool,
        feedback_score: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Rate instruction success/failure"""
        await self._ensure_initialized()
        
        logger.info("Rating instruction", instruction_id=instruction_id, success=success, feedback_score=feedback_score)
        
        await self.repository.record_instruction_usage(
            instruction_id, success, feedback_score, metadata
        )
    
    async def get_instruction_analytics(
        self,
        entity_name: Optional[str] = None,
        operation_type: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get instruction usage analytics"""
        await self._ensure_initialized()
        
        logger.info("Getting instruction analytics", entity_name=entity_name, operation_type=operation_type, hours=hours)
        
        return await self.repository.get_instruction_stats(entity_name=entity_name, hours=hours)
    
    # Service info
    async def get_service_info(self) -> Dict[str, Any]:
        """Get service implementation information"""
        repo_info = await self.repository.get_repository_info()
        
        return {
            "type": "instructions_service",
            "version": "1.0.0", 
            "initialized": self._initialized,
            "repository": repo_info,
            "capabilities": [
                "instruction_management",
                "instruction_search",
                "usage_analytics",
                "success_tracking"
            ]
        }
    
    # Private methods
    async def _ensure_initialized(self) -> None:
        """Ensure service is initialized"""
        if not self._initialized:
            await self.initialize()
    
    def _merge_instructions(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Intelligently merge two instructions"""
        merged = existing.copy()
        
        # Update basic fields
        if "title" in new:
            merged["title"] = new["title"]
        if "description" in new:
            # Append to existing description
            existing_desc = existing.get("description", "")
            new_desc = new["description"]
            merged["description"] = f"{existing_desc}\n\nAdditional notes: {new_desc}" if existing_desc else new_desc
        
        # Merge tags
        existing_tags = set(existing.get("tags", []))
        new_tags = set(new.get("tags", []))
        merged["tags"] = list(existing_tags | new_tags)
        
        # Keep most recent example data
        if "example_data" in new:
            merged["example_data"] = new["example_data"]
        if "example_query" in new:
            merged["example_query"] = new["example_query"]
        
        return merged
    
    def _extract_common_patterns(self, instructions: List[Dict[str, Any]]) -> List[str]:
        """Extract common patterns from instructions"""
        patterns = []
        
        # Analyze instruction content for patterns
        for instruction in instructions:
            inst_data = instruction.get("instruction", {})
            
            # Extract patterns from tags
            tags = inst_data.get("tags", [])
            if "successful" in tags:
                patterns.append(f"Proven successful pattern for {instruction['entity_name']}")
            
            # Extract patterns from descriptions
            description = inst_data.get("description", "")
            if "required" in description.lower():
                patterns.append("Pay attention to required fields")
            if "company" in description.lower() or "dataareaid" in description.lower():
                patterns.append("Consider company context for this entity")
        
        return list(set(patterns))  # Remove duplicates
    
    def _generate_suggestions(self, instructions: List[Dict[str, Any]]) -> List[str]:
        """Generate helpful suggestions based on instructions"""
        suggestions = []
        
        if instructions:
            latest_instruction = max(instructions, key=lambda x: x.get("updated_at", ""))
            inst_data = latest_instruction.get("instruction", {})
            
            suggestions.append("Review the latest successful patterns before proceeding")
            
            if "example_data" in inst_data:
                suggestions.append("Use the example_data as a template for your request")
            
            if "example_query" in inst_data:
                suggestions.append("Try the example_query for proven filtering approaches")
        
        return suggestions