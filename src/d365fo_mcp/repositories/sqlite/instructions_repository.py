"""
SQLite Instructions Repository Implementation

Stores entity instructions and usage analytics in SQLite database.
"""

import sqlite3
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import structlog

from ..instructions.interface import IInstructionsRepository
from .database import Database, DatabaseError

logger = structlog.get_logger(__name__)


class SQLiteInstructionsRepository(IInstructionsRepository):
    """SQLite implementation of instructions repository"""
    
    def __init__(self, db_path: Union[str, Path] = "./d365fo-mcp.db"):
        self.database = Database(db_path)
    
    async def initialize(self) -> None:
        """Initialize the repository and database"""
        await self.database.initialize()
        logger.info("SQLite instructions repository initialized")
    
    async def close(self) -> None:
        """Close repository connections"""
        await self.database.close()
    
    # Instruction operations
    async def save_instruction(
        self,
        entity_name: str,
        operation_type: str,
        instruction: Dict[str, Any]
    ) -> str:
        """Save a new instruction"""
        try:
            # Validate required fields
            if not instruction.get("title"):
                raise DatabaseError("Instruction title is required")
            if not instruction.get("description"):
                raise DatabaseError("Instruction description is required")
                
            connection = await self.database.get_connection()
            
            tags_json = json.dumps(instruction.get("tags", []), default=str)
            
            cursor = connection.execute("""
                INSERT INTO entity_instructions 
                (entity_name, operation_type, title, description, example_query, 
                 example_data, tags, success_count, failure_count, created_at, updated_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entity_name,
                operation_type,
                instruction["title"],
                instruction["description"],
                instruction.get("example_query"),
                instruction.get("example_data"),
                tags_json,
                0,  # success_count
                0,  # failure_count
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                instruction.get("created_by")
            ))
            
            instruction_id = str(cursor.lastrowid)
            
            connection.commit()
            logger.info("Saved instruction", entity_name=entity_name, operation_type=operation_type, instruction_id=instruction_id)
            
            return instruction_id
            
        except Exception as e:
            logger.error("Failed to save instruction", entity_name=entity_name, error=str(e))
            raise DatabaseError(f"Failed to save instruction: {e}")
    
    async def update_instruction(
        self,
        instruction_id: str,
        instruction: Dict[str, Any]
    ) -> None:
        """Update an existing instruction"""
        try:
            connection = await self.database.get_connection()
            
            tags_json = json.dumps(instruction.get("tags", []), default=str)
            
            cursor = connection.execute("""
                UPDATE entity_instructions 
                SET title = ?, description = ?, example_query = ?, example_data = ?, 
                    tags = ?, updated_at = ?
                WHERE id = ?
            """, (
                instruction.get("title", ""),
                instruction.get("description", ""),
                instruction.get("example_query"),
                instruction.get("example_data"),
                tags_json,
                datetime.now().isoformat(),
                instruction_id
            ))
            
            if cursor.rowcount == 0:
                raise DatabaseError(f"Instruction {instruction_id} not found")
            
            connection.commit()
            logger.info("Updated instruction", instruction_id=instruction_id)
            
        except Exception as e:
            logger.error("Failed to update instruction", instruction_id=instruction_id, error=str(e))
            raise DatabaseError(f"Failed to update instruction: {e}")
    
    async def get_instruction(self, instruction_id: str) -> Optional[Dict[str, Any]]:
        """Get instruction by ID"""
        try:
            connection = await self.database.get_connection()
            
            cursor = connection.execute("""
                SELECT entity_name, operation_type, instruction, created_at, updated_at
                FROM entity_instructions 
                WHERE id = ?
            """, (instruction_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "id": instruction_id,
                    "entity_name": row[0],
                    "operation_type": row[1], 
                    "instruction": json.loads(row[2]),
                    "created_at": row[3],
                    "updated_at": row[4]
                }
            
            return None
            
        except Exception as e:
            logger.error("Failed to get instruction", instruction_id=instruction_id, error=str(e))
            return None
    
    async def get_entity_instructions(
        self,
        entity_name: str,
        operation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get instructions for an entity and operation"""
        try:
            connection = await self.database.get_connection()
            
            if operation_type:
                cursor = connection.execute("""
                    SELECT id, operation_type, title, description, example_query, 
                           example_data, tags, success_count, failure_count, 
                           created_at, updated_at, created_by
                    FROM entity_instructions 
                    WHERE entity_name = ? AND operation_type = ?
                    ORDER BY updated_at DESC
                """, (entity_name, operation_type))
            else:
                cursor = connection.execute("""
                    SELECT id, operation_type, title, description, example_query, 
                           example_data, tags, success_count, failure_count, 
                           created_at, updated_at, created_by
                    FROM entity_instructions 
                    WHERE entity_name = ?
                    ORDER BY operation_type, updated_at DESC
                """, (entity_name,))
            
            instructions = []
            for row in cursor.fetchall():
                instructions.append({
                    "id": row[0],
                    "entity_name": entity_name,
                    "operation_type": row[1],
                    "title": row[2],
                    "description": row[3],
                    "example_query": row[4],
                    "example_data": row[5],
                    "tags": json.loads(row[6]) if row[6] else [],
                    "success_count": row[7] or 0,
                    "failure_count": row[8] or 0,
                    "created_at": row[9],
                    "updated_at": row[10],
                    "created_by": row[11]
                })
            
            return instructions
            
        except Exception as e:
            logger.error("Failed to get entity instructions", entity_name=entity_name, error=str(e))
            return []
    
    async def search_instructions(
        self,
        query: str,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Search instructions by content"""
        try:
            connection = await self.database.get_connection()
            
            search_pattern = f"%{query}%"
            
            cursor = connection.execute("""
                SELECT id, entity_name, operation_type, title, description, example_query, 
                       example_data, tags, success_count, failure_count, 
                       created_at, updated_at, created_by
                FROM entity_instructions 
                WHERE entity_name LIKE ? OR title LIKE ? OR description LIKE ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """, (search_pattern, search_pattern, search_pattern, limit, skip))
            
            instructions = []
            for row in cursor.fetchall():
                instructions.append({
                    "id": row[0],
                    "entity_name": row[1],
                    "operation_type": row[2],
                    "title": row[3],
                    "description": row[4],
                    "example_query": row[5],
                    "example_data": row[6],
                    "tags": json.loads(row[7]) if row[7] else [],
                    "success_count": row[8] or 0,
                    "failure_count": row[9] or 0,
                    "created_at": row[10],
                    "updated_at": row[11],
                    "created_by": row[12]
                })
            
            return instructions
            
        except Exception as e:
            logger.error("Failed to search instructions", query=query, error=str(e))
            return []
    
    async def delete_instruction(self, instruction_id: str) -> bool:
        """Delete an instruction"""
        try:
            connection = await self.database.get_connection()
            
            cursor = connection.execute("""
                DELETE FROM entity_instructions WHERE id = ?
            """, (instruction_id,))
            
            connection.commit()
            
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info("Deleted instruction", instruction_id=instruction_id)
            
            return deleted
            
        except Exception as e:
            logger.error("Failed to delete instruction", instruction_id=instruction_id, error=str(e))
            return False
    
    # Statistics and analytics
    async def record_instruction_usage(
        self,
        instruction_id: str,
        success: bool = True,
        feedback_score: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record instruction usage statistics"""
        try:
            connection = await self.database.get_connection()
            
            metadata_json = json.dumps(metadata or {}, default=str)
            
            connection.execute("""
                INSERT INTO instruction_usage_stats 
                (instruction_id, success, feedback_score, metadata, recorded_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                instruction_id,
                success,
                feedback_score,
                metadata_json,
                datetime.now().isoformat()
            ))
            
            # Update success/failure counts in main table
            if success:
                connection.execute("""
                    UPDATE entity_instructions 
                    SET success_count = success_count + 1, updated_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), instruction_id))
            else:
                connection.execute("""
                    UPDATE entity_instructions 
                    SET failure_count = failure_count + 1, updated_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), instruction_id))
            
            connection.commit()
            logger.info("Recorded instruction usage", instruction_id=instruction_id, success=success)
            
        except Exception as e:
            logger.error("Failed to record instruction usage", instruction_id=instruction_id, error=str(e))
            raise DatabaseError(f"Failed to record instruction usage: {e}")
    
    async def get_instruction_stats(
        self,
        instruction_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get instruction usage statistics"""
        try:
            connection = await self.database.get_connection()
            
            # Base time filter
            time_filter = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            if instruction_id:
                # Stats for specific instruction
                cursor = connection.execute("""
                    SELECT COUNT(*) as total_uses,
                           SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_uses,
                           AVG(CASE WHEN feedback_score IS NOT NULL THEN feedback_score END) as avg_feedback
                    FROM instruction_usage_stats 
                    WHERE instruction_id = ? AND recorded_at > ?
                """, (instruction_id, time_filter))
                
                row = cursor.fetchone()
                
                return {
                    "instruction_id": instruction_id,
                    "total_uses": row[0] or 0,
                    "successful_uses": row[1] or 0,
                    "success_rate": (row[1] / row[0]) if row[0] > 0 else 0,
                    "average_feedback": row[2] or 0
                }
                
            elif entity_name:
                # Stats for entity instructions
                cursor = connection.execute("""
                    SELECT ei.operation_type,
                           COUNT(ius.instruction_id) as total_uses,
                           SUM(CASE WHEN ius.success THEN 1 ELSE 0 END) as successful_uses
                    FROM entity_instructions ei
                    LEFT JOIN instruction_usage_stats ius ON ei.id = ius.instruction_id AND ius.recorded_at > ?
                    WHERE ei.entity_name = ?
                    GROUP BY ei.operation_type
                """, (time_filter, entity_name))
                
                operations = {}
                for row in cursor.fetchall():
                    operations[row[0]] = {
                        "total_uses": row[1] or 0,
                        "successful_uses": row[2] or 0,
                        "success_rate": (row[2] / row[1]) if row[1] > 0 else 0
                    }
                
                return {
                    "entity_name": entity_name,
                    "operations": operations
                }
            
            else:
                # Overall stats
                cursor = connection.execute("""
                    SELECT COUNT(*) as total_uses,
                           SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_uses,
                           COUNT(DISTINCT instruction_id) as instructions_used
                    FROM instruction_usage_stats 
                    WHERE recorded_at > ?
                """, (time_filter,))
                
                row = cursor.fetchone()
                
                return {
                    "total_uses": row[0] or 0,
                    "successful_uses": row[1] or 0,
                    "success_rate": (row[1] / row[0]) if row[0] > 0 else 0,
                    "instructions_used": row[2] or 0
                }
            
        except Exception as e:
            logger.error("Failed to get instruction stats", error=str(e))
            return {"error": str(e)}
    
    async def get_repository_info(self) -> Dict[str, Any]:
        """Get repository implementation information"""
        try:
            connection = await self.database.get_connection()
            
            # Get basic stats
            cursor = connection.execute("SELECT COUNT(*) FROM entity_instructions")
            total_instructions = cursor.fetchone()[0]
            
            cursor = connection.execute("""
                SELECT COUNT(*) FROM instruction_usage_stats 
                WHERE recorded_at > ?
            """, ((datetime.now() - timedelta(days=1)).isoformat(),))
            daily_usage = cursor.fetchone()[0]
            
            return {
                "type": "sqlite_instructions_repository",
                "version": "1.0.0",
                "database_path": str(self.database.db_path),
                "total_instructions": total_instructions,
                "daily_usage": daily_usage,
                "capabilities": [
                    "instruction_storage",
                    "instruction_search",
                    "usage_analytics",
                    "feedback_tracking"
                ]
            }
            
        except Exception as e:
            logger.error("Failed to get repository info", error=str(e))
            return {
                "type": "sqlite_instructions_repository", 
                "error": str(e)
            }