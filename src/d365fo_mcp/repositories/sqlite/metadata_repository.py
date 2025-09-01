"""
SQLite Metadata Repository Implementation

Provides high-performance metadata operations using optimized SQLite queries.
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import structlog

from ..metadata.interface import IMetadataRepository
from .database import Database, DatabaseError

logger = structlog.get_logger(__name__)

# Optimized queries for high-performance metadata operations
OPTIMIZED_QUERIES = {
    "search_entities": """
        SELECT 
            es.name as entity_set_name,
            et.name as entity_type_name,
            es.name as use_for_queries,
            'D365 entity: ' || et.name as description,
            (CASE 
                WHEN lower(es.name) = lower(?) THEN 100
                WHEN lower(et.name) = lower(?) THEN 100  
                WHEN lower(es.name) LIKE lower(?) || '%' THEN 50
                WHEN lower(et.name) LIKE lower(?) || '%' THEN 50
                WHEN lower(es.name) LIKE '%' || lower(?) || '%' THEN 25
                WHEN lower(et.name) LIKE '%' || lower(?) || '%' THEN 25
                ELSE 0
            END) as relevance
        FROM entity_sets es
        JOIN entity_types et ON es.entity_type_id = et.id
        WHERE relevance > 0
        ORDER BY relevance DESC, es.name ASC
        LIMIT ? OFFSET ?
    """,
    
    "search_entities_count": """
        SELECT COUNT(*) as total
        FROM entity_sets es
        JOIN entity_types et ON es.entity_type_id = et.id
        WHERE lower(es.name) LIKE '%' || lower(?) || '%'
           OR lower(et.name) LIKE '%' || lower(?) || '%'
    """,
    
    "get_entity_metadata": """
        SELECT 
            et.name as entity_type_name,
            es.name as entity_set_name,
            es.name as use_for_queries,
            et.base_type,
            et.abstract,
            et.has_key,
            COUNT(DISTINCT ep.id) as field_count,
            COUNT(DISTINCT np.id) as relationship_count
        FROM entity_types et
        JOIN entity_sets es ON es.entity_type_id = et.id
        LEFT JOIN entity_properties ep ON ep.entity_type_id = et.id
        LEFT JOIN navigation_properties np ON np.entity_type_id = et.id
        WHERE et.name = ? OR es.name = ?
        GROUP BY et.id, es.id
    """,
    
    "get_entity_properties": """
        SELECT 
            name, type, nullable, max_length, precision, scale,
            is_key, is_enum, enum_type, annotations, ordinal_position
        FROM entity_properties
        WHERE entity_type_id = (
            SELECT et.id FROM entity_types et
            LEFT JOIN entity_sets es ON es.entity_type_id = et.id
            WHERE et.name = ? OR es.name = ?
            LIMIT 1
        )
        ORDER BY ordinal_position ASC, name ASC
    """,
    
    "get_navigation_properties": """
        SELECT 
            name, target_entity_type, relationship_type, 
            is_collection, nullable, annotations
        FROM navigation_properties
        WHERE entity_type_id = (
            SELECT et.id FROM entity_types et
            LEFT JOIN entity_sets es ON es.entity_type_id = et.id
            WHERE et.name = ? OR es.name = ?
            LIMIT 1
        )
        ORDER BY name ASC
    """,
}


class SQLiteMetadataRepository(IMetadataRepository):
    """SQLite implementation of metadata repository with performance optimizations"""
    
    def __init__(self, db_path: Union[str, Path] = "./d365fo-mcp.db"):
        self.database = Database(db_path)
    
    async def initialize(self) -> None:
        """Initialize the repository and database"""
        await self.database.initialize()
        logger.info("SQLite metadata repository initialized")
    
    async def close(self) -> None:
        """Close repository connections"""
        await self.database.close()
    
    async def search_entities(self, pattern: str, limit: int = 20, skip: int = 0) -> Dict[str, Any]:
        """
        High-performance entity search using SQLite indexes with pagination info.
        
        Returns structured result with entities list and pagination metadata.
        """
        start_time = time.time()
        
        try:
            connection = await self.database.get_connection()
            
            # Get matching entities with relevance scoring
            cursor = connection.execute(
                OPTIMIZED_QUERIES["search_entities"],
                (pattern, pattern, pattern, pattern, pattern, pattern, limit, skip)
            )
            
            matches = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                matches.append({
                    "entity_name": row_dict["entity_type_name"],
                    "entity_set": row_dict["entity_set_name"],
                    "use_for_queries": row_dict["use_for_queries"],
                    "description": row_dict["description"],
                    "relevance": row_dict["relevance"]
                })
            
            # Get total count for pagination
            cursor = connection.execute(
                OPTIMIZED_QUERIES["search_entities_count"],
                (pattern, pattern)
            )
            total_row = cursor.fetchone()
            total_matches = total_row["total"] if total_row else 0
            
            query_time_ms = (time.time() - start_time) * 1000
            
            logger.debug("Entity search completed",
                        pattern=pattern,
                        results=len(matches), 
                        query_time_ms=query_time_ms)
            
            return {
                "entities": [m["entity_name"] for m in matches],
                "detailed_entities": matches,
                "pagination_info": {
                    "total_matches": total_matches,
                    "returned_count": len(matches),
                    "skip": skip,
                    "limit": limit,
                    "has_more": (skip + limit) < total_matches
                },
                "pagination_guidance": {
                    "next_page": f"search_entities(pattern='{pattern}', limit={limit}, skip={skip + limit})" if (skip + limit) < total_matches else None,
                    "to_get_all": "Increase limit or use multiple calls with skip parameter"
                },
                "_performance": {
                    "query_time_ms": query_time_ms,
                    "source": "high_performance_sqlite"
                }
            }
            
        except Exception as e:
            logger.error("Failed to search entities", pattern=pattern, error=str(e))
            raise DatabaseError(f"Failed to search entities for pattern '{pattern}': {e}")
    
    async def get_cached_entity_metadata(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive entity metadata from populated database.
        """
        start_time = time.time()
        
        try:
            connection = await self.database.get_connection()
            
            # Get basic entity info
            cursor = connection.execute(
                OPTIMIZED_QUERIES["get_entity_metadata"],
                (entity_name, entity_name)
            )
            
            entity_row = cursor.fetchone()
            if not entity_row:
                logger.debug("Entity not found", entity_name=entity_name)
                return None
            
            entity_info = dict(entity_row)
            
            # Get properties
            cursor = connection.execute(
                OPTIMIZED_QUERIES["get_entity_properties"],
                (entity_name, entity_name)
            )
            
            fields = []
            key_fields = []
            
            for prop_row in cursor.fetchall():
                prop = dict(prop_row)
                
                field = {
                    "name": prop["name"],
                    "type": prop["type"],
                    "nullable": bool(prop["nullable"]),
                    "max_length": prop["max_length"],
                    "precision": prop["precision"], 
                    "scale": prop["scale"],
                    "is_enum": bool(prop["is_enum"])
                }
                
                if prop["is_enum"] and prop["enum_type"]:
                    field["enum_name"] = prop["enum_type"]
                    field["odata_syntax"] = f"Microsoft.Dynamics.DataEntities.{prop['enum_type']}"
                
                fields.append(field)
                
                if prop["is_key"]:
                    key_fields.append(prop["name"])
            
            # Get navigation properties
            cursor = connection.execute(
                OPTIMIZED_QUERIES["get_navigation_properties"],
                (entity_name, entity_name)
            )
            
            navigation_properties = {}
            for nav_row in cursor.fetchall():
                nav = dict(nav_row)
                navigation_properties[nav["name"]] = {
                    "target_entity": nav["target_entity_type"],
                    "relationship_type": nav["relationship_type"],
                    "is_collection": bool(nav["is_collection"]),
                    "nullable": bool(nav["nullable"])
                }
            
            query_time_ms = (time.time() - start_time) * 1000
            
            result = {
                "entity_name": entity_info["entity_type_name"],
                "entity_set_name": entity_info["entity_set_name"],
                "use_for_queries": entity_info["use_for_queries"],
                "fields": fields,
                "key_fields": key_fields,
                "field_count": len(fields),
                "navigation_properties": navigation_properties,
                "relationship_count": len(navigation_properties),
                "query_example": f'get_odata_entity("{entity_info["use_for_queries"]}", "?$top=10")',
                "_performance": {
                    "query_time_ms": query_time_ms,
                    "source": "high_performance_sqlite"
                }
            }
            
            logger.debug("Entity metadata retrieved",
                        entity_name=entity_name,
                        field_count=len(fields),
                        query_time_ms=query_time_ms)
            
            return result
            
        except Exception as e:
            logger.error("Failed to get entity metadata", entity_name=entity_name, error=str(e))
            raise DatabaseError(f"Failed to get metadata for entity '{entity_name}': {e}")
    
    # Implement other required interface methods with basic implementations
    async def cache_entity_metadata(self, entity_name: str, metadata: Dict[str, Any]) -> None:
        """Cache entity metadata (not needed for pre-populated database)"""
        logger.debug("Cache entity metadata called (no-op for pre-populated DB)", entity_name=entity_name)
        pass
    
    async def list_cached_entities(self) -> List[Dict[str, Any]]:
        """List all cached entities with basic metadata"""
        try:
            connection = await self.database.get_connection()
            
            cursor = connection.execute("""
                SELECT es.name as entity_set_name, et.name as entity_type_name,
                       es.name as use_for_queries,
                       'D365 entity: ' || et.name as description
                FROM entity_sets es
                JOIN entity_types et ON es.entity_type_id = et.id
                ORDER BY es.name
                LIMIT 1000
            """)
            
            entities = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                entities.append({
                    "entity_name": row_dict["entity_type_name"],
                    "entity_set": row_dict["entity_set_name"],
                    "use_for_queries": row_dict["use_for_queries"],
                    "description": row_dict["description"]
                })
            
            return entities
            
        except Exception as e:
            logger.error("Failed to list cached entities", error=str(e))
            raise DatabaseError(f"Failed to list entities: {e}")
    
    async def cache_raw_metadata(self, metadata_xml: str) -> None:
        """Cache raw metadata XML (not needed for pre-populated database)"""
        logger.debug("Cache raw metadata called (no-op for pre-populated DB)")
        pass
    
    async def get_cached_raw_metadata(self) -> Optional[str]:
        """Get cached raw metadata XML (not applicable)"""
        return None
    
    async def is_metadata_cache_valid(self) -> bool:
        """Check if metadata cache is valid (always true for pre-populated DB)"""
        connection = await self.database.get_connection()
        cursor = connection.execute("SELECT COUNT(*) as count FROM entity_types")
        row = cursor.fetchone()
        return row and row["count"] > 0
    
    async def search_enums(self, pattern: str, limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
        """Search for enums by name pattern"""
        try:
            connection = await self.database.get_connection()
            
            cursor = connection.execute("""
                SELECT name,
                    (CASE 
                        WHEN lower(name) = lower(?) THEN 100
                        WHEN lower(name) LIKE lower(?) || '%' THEN 50
                        WHEN lower(name) LIKE '%' || lower(?) || '%' THEN 25
                        ELSE 0
                    END) as relevance
                FROM enum_types
                WHERE relevance > 0
                ORDER BY relevance DESC, name ASC
                LIMIT ? OFFSET ?
            """, (pattern, pattern, pattern, limit, skip))
            
            return [{"name": dict(row)["name"], "relevance": dict(row)["relevance"]} 
                    for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error("Failed to search enums", pattern=pattern, error=str(e))
            raise DatabaseError(f"Failed to search enums for pattern '{pattern}': {e}")
    
    async def get_enum_metadata(self, enum_name: str) -> Optional[Dict[str, Any]]:
        """Get enum metadata with all values"""
        try:
            connection = await self.database.get_connection()
            
            cursor = connection.execute("""
                SELECT 
                    et.name, et.underlying_type, et.is_flags, et.namespace,
                    em.name as member_name, em.value as member_value,
                    em.annotations as member_annotations, em.ordinal_position
                FROM enum_types et
                LEFT JOIN enum_members em ON em.enum_type_id = et.id
                WHERE et.name = ?
                ORDER BY em.ordinal_position ASC, em.name ASC
            """, (enum_name,))
            
            rows = cursor.fetchall()
            if not rows:
                return None
            
            first_row = dict(rows[0])
            
            members = []
            for row in rows:
                row_dict = dict(row)
                if row_dict["member_name"]:
                    members.append({
                        "name": row_dict["member_name"],
                        "value": row_dict["member_value"],
                        "odata_syntax": f"Microsoft.Dynamics.DataEntities.{enum_name}'{row_dict['member_name']}'",
                        "annotations": json.loads(row_dict["member_annotations"]) if row_dict.get("member_annotations") else {}
                    })
            
            return {
                "name": first_row["name"],
                "member_count": len(members),
                "members": members,
                "underlying_type": first_row["underlying_type"],
                "is_flags": bool(first_row["is_flags"]),
                "annotations": {}
            }
            
        except Exception as e:
            logger.error("Failed to get enum metadata", enum_name=enum_name, error=str(e))
            raise DatabaseError(f"Failed to get enum metadata for '{enum_name}': {e}")
    
    async def get_entity_enum_fields(self, entity_name: str) -> Dict[str, Any]:
        """Get all enum fields for an entity"""
        try:
            connection = await self.database.get_connection()
            
            cursor = connection.execute("""
                SELECT 
                    ep.name as field_name,
                    ep.enum_type,
                    'Microsoft.Dynamics.DataEntities.' || ep.enum_type as odata_syntax
                FROM entity_properties ep
                JOIN entity_types et ON ep.entity_type_id = et.id
                LEFT JOIN entity_sets es ON es.entity_type_id = et.id
                WHERE ep.is_enum = 1 AND (et.name = ? OR es.name = ?)
                ORDER BY ep.name ASC
            """, (entity_name, entity_name))
            
            enum_fields = {}
            for row in cursor.fetchall():
                row_dict = dict(row)
                enum_fields[row_dict["field_name"]] = {
                    "enum_name": row_dict["enum_type"],
                    "odata_syntax": row_dict["odata_syntax"]
                }
            
            return enum_fields
            
        except Exception as e:
            logger.error("Failed to get entity enum fields", entity_name=entity_name, error=str(e))
            raise DatabaseError(f"Failed to get enum fields for entity '{entity_name}': {e}")
    
    async def clear_metadata_cache(self) -> None:
        """Clear all metadata cache"""
        logger.warning("Clear metadata cache called on pre-populated database - this will remove all data!")
        # Implement if needed, but be careful as this removes all parsed data
        pass
    
    async def record_usage_stat(
        self,
        operation: str,
        entity_name: Optional[str] = None,
        success: bool = True,
        execution_time_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record usage statistics (optional for performance reasons)"""
        logger.debug("Usage stat recorded", operation=operation, entity_name=entity_name, success=success)
        # Could implement if usage tracking is needed
        pass
    
    async def get_usage_stats(
        self,
        operation: Optional[str] = None,
        entity_name: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get usage statistics"""
        return []  # Return empty list if not tracking usage
    
    async def get_repository_info(self) -> Dict[str, Any]:
        """Get repository implementation information"""
        connection = await self.database.get_connection()
        
        # Get counts
        cursor = connection.execute("SELECT COUNT(*) as count FROM entity_types")
        entity_count = cursor.fetchone()["count"]
        
        cursor = connection.execute("SELECT COUNT(*) as count FROM enum_types")
        enum_count = cursor.fetchone()["count"]
        
        return {
            "repository_type": "SQLiteMetadataRepository",
            "backend": "SQLite",
            "database_path": str(self.database.db_path),
            "entity_count": entity_count,
            "enum_count": enum_count,
            "capabilities": [
                "high_performance_search",
                "relevance_scoring", 
                "bulk_metadata_access",
                "enum_support",
                "navigation_properties"
            ],
            "performance_optimizations": [
                "sqlite_indexes",
                "relevance_scoring",
                "optimized_queries",
                "wal_mode"
            ]
        }