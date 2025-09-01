"""
High-performance bulk XML parser for D365 metadata

Optimized for parsing 46MB XML files and storing in SQLite with maximum efficiency.
"""

import xml.etree.ElementTree as ET
import sqlite3
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager
import structlog

logger = structlog.get_logger(__name__)

class BulkMetadataParser:
    """High-performance parser for D365 OData metadata XML"""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.db = db_connection
        self.db.execute("PRAGMA journal_mode = WAL")
        self.db.execute("PRAGMA synchronous = NORMAL")
        self.db.execute("PRAGMA cache_size = -64000")  # 64MB cache
        self.db.execute("PRAGMA temp_store = MEMORY")
        
    async def parse_and_store_metadata(
        self, 
        metadata_xml: str, 
        d365_instance: str,
        chunk_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Parse full metadata XML and store in SQLite with maximum performance.
        
        Args:
            metadata_xml: Full D365 OData metadata XML
            d365_instance: D365 instance identifier
            chunk_size: Batch size for database inserts
            
        Returns:
            Parsing statistics and performance metrics
        """
        start_time = time.time()
        
        logger.info("Starting bulk metadata parsing", 
                   xml_size=len(metadata_xml), 
                   d365_instance=d365_instance)
        
        try:
            # Parse XML once
            root = ET.fromstring(metadata_xml)
            
            # Track parsing statistics
            stats = {
                "xml_size_bytes": len(metadata_xml),
                "d365_instance": d365_instance,
                "entity_types_parsed": 0,
                "entity_sets_parsed": 0,  
                "properties_parsed": 0,
                "navigation_props_parsed": 0,
                "enum_types_parsed": 0,
                "enum_members_parsed": 0,
                "parsing_start": datetime.now(),
                "phases": {}
            }
            
            with self._transaction():
                # Phase 1: Parse and store entity types
                phase_start = time.time()
                entity_type_map = await self._parse_entity_types(root, chunk_size)
                stats["entity_types_parsed"] = len(entity_type_map)
                stats["phases"]["entity_types"] = time.time() - phase_start
                
                # Phase 2: Parse and store entity sets
                phase_start = time.time()
                entity_set_map = await self._parse_entity_sets(root, entity_type_map, chunk_size)
                stats["entity_sets_parsed"] = len(entity_set_map)
                stats["phases"]["entity_sets"] = time.time() - phase_start
                
                # Phase 3: Parse and store properties (bulk insert)
                phase_start = time.time()
                properties_count = await self._parse_entity_properties(root, entity_type_map, chunk_size)
                stats["properties_parsed"] = properties_count
                stats["phases"]["properties"] = time.time() - phase_start
                
                # Phase 4: Parse and store navigation properties
                phase_start = time.time()
                nav_props_count = await self._parse_navigation_properties(root, entity_type_map, chunk_size)
                stats["navigation_props_parsed"] = nav_props_count
                stats["phases"]["navigation_properties"] = time.time() - phase_start
                
                # Phase 5: Parse and store enum types
                phase_start = time.time()
                enum_type_map = await self._parse_enum_types(root, chunk_size)
                stats["enum_types_parsed"] = len(enum_type_map)
                stats["phases"]["enum_types"] = time.time() - phase_start
                
                # Phase 6: Parse and store enum members
                phase_start = time.time()
                enum_members_count = await self._parse_enum_members(root, enum_type_map, chunk_size)
                stats["enum_members_parsed"] = enum_members_count
                stats["phases"]["enum_members"] = time.time() - phase_start
                
                # Phase 7: Update FTS search index
                phase_start = time.time()
                await self._update_search_index(entity_set_map, enum_type_map)
                stats["phases"]["search_index"] = time.time() - phase_start
                
                # Record sync metadata
                await self._record_sync_metadata(stats)
                
            total_time = time.time() - start_time
            stats["total_duration_seconds"] = total_time
            stats["records_per_second"] = (
                stats["properties_parsed"] + stats["enum_members_parsed"]
            ) / max(total_time, 0.001)
            
            logger.info("Bulk metadata parsing completed",
                       total_duration=total_time,
                       entities=stats["entity_types_parsed"],
                       properties=stats["properties_parsed"],
                       enums=stats["enum_types_parsed"],
                       records_per_sec=stats["records_per_second"])
            
            return stats
            
        except Exception as e:
            logger.error("Bulk parsing failed", error=str(e))
            raise
    
    @contextmanager
    def _transaction(self):
        """Context manager for database transactions with optimization"""
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
    
    async def _parse_entity_types(
        self, 
        root: ET.Element, 
        chunk_size: int
    ) -> Dict[str, int]:
        """Parse EntityType definitions with bulk insert"""
        
        entity_types_batch = []
        entity_type_map = {}  # name -> id
        
        for entity_type in root.findall(".//{http://docs.oasis-open.org/odata/ns/edm}EntityType"):
            name = entity_type.get("Name")
            if not name:
                continue
                
            # Parse entity type attributes
            base_type = entity_type.get("BaseType")
            abstract = entity_type.get("Abstract", "false").lower() == "true"
            
            # Check if has key
            key_element = entity_type.find("./{http://docs.oasis-open.org/odata/ns/edm}Key")
            has_key = key_element is not None
            
            # Extract namespace from qualified name
            namespace = "Microsoft.Dynamics.DataEntities"  # Default for D365
            
            # Parse annotations
            annotations = self._parse_annotations(entity_type)
            
            entity_types_batch.append((
                name, base_type, abstract, has_key, namespace, 
                json.dumps(annotations) if annotations else None
            ))
            
            if len(entity_types_batch) >= chunk_size:
                await self._flush_entity_types_batch(entity_types_batch, entity_type_map)
                entity_types_batch = []
        
        # Flush remaining
        if entity_types_batch:
            await self._flush_entity_types_batch(entity_types_batch, entity_type_map)
            
        return entity_type_map
    
    async def _flush_entity_types_batch(
        self, 
        batch: List[Tuple], 
        entity_type_map: Dict[str, int]
    ):
        """Bulk insert entity types and update mapping"""
        cursor = self.db.executemany("""
            INSERT INTO entity_types (name, base_type, abstract, has_key, namespace, annotations)
            VALUES (?, ?, ?, ?, ?, ?)
        """, batch)
        
        # Get IDs for mapping (SQLite doesn't support RETURNING with executemany)
        last_rowid = cursor.lastrowid
        if last_rowid is not None:
            start_id = last_rowid - len(batch) + 1
            for i, (name, *_) in enumerate(batch):
                entity_type_map[name] = start_id + i
        else:
            # Fallback: query for the IDs
            for name, *_ in batch:
                cursor = self.db.execute("SELECT id FROM entity_types WHERE name = ?", (name,))
                row = cursor.fetchone()
                if row:
                    entity_type_map[name] = row[0]
    
    async def _parse_entity_sets(
        self, 
        root: ET.Element, 
        entity_type_map: Dict[str, int],
        chunk_size: int
    ) -> Dict[str, Dict[str, Any]]:
        """Parse EntitySet definitions"""
        
        entity_sets_batch = []
        entity_set_map = {}
        
        # Find EntityContainer
        container = root.find(".//{http://docs.oasis-open.org/odata/ns/edm}EntityContainer")
        if container is None:
            logger.warning("EntityContainer not found in metadata")
            return entity_set_map
        
        for entity_set in container.findall(".//{http://docs.oasis-open.org/odata/ns/edm}EntitySet"):
            set_name = entity_set.get("Name")
            entity_type_ref = entity_set.get("EntityType")
            
            if not set_name or not entity_type_ref:
                continue
                
            # Extract entity type name (remove namespace)
            entity_type_name = entity_type_ref.split(".")[-1]
            entity_type_id = entity_type_map.get(entity_type_name)
            
            if not entity_type_id:
                logger.warning("EntityType not found for EntitySet", 
                              set_name=set_name, entity_type=entity_type_name)
                continue
            
            annotations = self._parse_annotations(entity_set)
            
            entity_sets_batch.append((
                set_name, entity_type_id,
                json.dumps(annotations) if annotations else None
            ))
            
            entity_set_map[set_name] = {
                "entity_type_name": entity_type_name,
                "entity_type_id": entity_type_id
            }
            
            if len(entity_sets_batch) >= chunk_size:
                self.db.executemany("""
                    INSERT INTO entity_sets (name, entity_type_id, annotations)
                    VALUES (?, ?, ?)
                """, entity_sets_batch)
                entity_sets_batch = []
        
        # Flush remaining
        if entity_sets_batch:
            self.db.executemany("""
                INSERT INTO entity_sets (name, entity_type_id, annotations)
                VALUES (?, ?, ?)
            """, entity_sets_batch)
            
        return entity_set_map
    
    async def _parse_entity_properties(
        self, 
        root: ET.Element,
        entity_type_map: Dict[str, int],
        chunk_size: int
    ) -> int:
        """Parse all entity properties with high-performance bulk insert"""
        
        properties_batch = []
        total_properties = 0
        
        for entity_type in root.findall(".//{http://docs.oasis-open.org/odata/ns/edm}EntityType"):
            entity_type_name = entity_type.get("Name")
            if not entity_type_name:
                continue
                
            entity_type_id = entity_type_map.get(entity_type_name)
            if not entity_type_id:
                continue
            
            # Get key fields for this entity
            key_fields = set()
            key_element = entity_type.find("./{http://docs.oasis-open.org/odata/ns/edm}Key")
            if key_element is not None:
                for key_ref in key_element.findall("./{http://docs.oasis-open.org/odata/ns/edm}PropertyRef"):
                    key_name = key_ref.get("Name")
                    if key_name:
                        key_fields.add(key_name)
            
            # Parse properties for this entity
            ordinal = 0
            for prop in entity_type.findall("./{http://docs.oasis-open.org/odata/ns/edm}Property"):
                prop_name = prop.get("Name")
                if not prop_name:
                    continue
                    
                prop_type = prop.get("Type", "")
                nullable = prop.get("Nullable", "true").lower() == "true"
                max_length = prop.get("MaxLength")
                precision = prop.get("Precision")
                scale = prop.get("Scale")
                is_key = prop_name in key_fields
                
                # Detect enum types
                is_enum = "Microsoft.Dynamics" in prop_type and "Enum" in prop_type
                enum_type = prop_type.split(".")[-1] if is_enum else None
                
                annotations = self._parse_annotations(prop)
                
                properties_batch.append((
                    entity_type_id, prop_name, prop_type, nullable,
                    int(max_length) if max_length and max_length.isdigit() else None,
                    int(precision) if precision and precision.isdigit() else None,
                    int(scale) if scale and scale.isdigit() else None,
                    is_key, is_enum, enum_type,
                    json.dumps(annotations) if annotations else None,
                    ordinal
                ))
                
                ordinal += 1
                total_properties += 1
                
                if len(properties_batch) >= chunk_size:
                    self.db.executemany("""
                        INSERT INTO entity_properties (
                            entity_type_id, name, type, nullable, max_length,
                            precision, scale, is_key, is_enum, enum_type,
                            annotations, ordinal_position
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, properties_batch)
                    properties_batch = []
        
        # Flush remaining
        if properties_batch:
            self.db.executemany("""
                INSERT INTO entity_properties (
                    entity_type_id, name, type, nullable, max_length,
                    precision, scale, is_key, is_enum, enum_type,
                    annotations, ordinal_position
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, properties_batch)
            
        return total_properties
    
    async def _parse_navigation_properties(
        self,
        root: ET.Element,
        entity_type_map: Dict[str, int],
        chunk_size: int
    ) -> int:
        """Parse navigation properties for relationships"""
        
        nav_props_batch = []
        total_nav_props = 0
        
        for entity_type in root.findall(".//{http://docs.oasis-open.org/odata/ns/edm}EntityType"):
            entity_type_name = entity_type.get("Name")
            if not entity_type_name:
                continue
                
            entity_type_id = entity_type_map.get(entity_type_name)
            if not entity_type_id:
                continue
            
            for nav_prop in entity_type.findall("./{http://docs.oasis-open.org/odata/ns/edm}NavigationProperty"):
                prop_name = nav_prop.get("Name")
                prop_type = nav_prop.get("Type", "")
                
                if not prop_name:
                    continue
                
                # Determine relationship type
                is_collection = prop_type.startswith("Collection(")
                nullable = nav_prop.get("Nullable", "true").lower() == "true"
                
                # Extract target entity type
                if is_collection:
                    target_entity = prop_type.replace("Collection(", "").replace(")", "").split(".")[-1]
                    relationship_type = "one_to_many"
                else:
                    target_entity = prop_type.split(".")[-1] if "." in prop_type else prop_type
                    relationship_type = "many_to_one"
                
                annotations = self._parse_annotations(nav_prop)
                
                nav_props_batch.append((
                    entity_type_id, prop_name, target_entity, relationship_type,
                    is_collection, nullable,
                    json.dumps(annotations) if annotations else None
                ))
                
                total_nav_props += 1
                
                if len(nav_props_batch) >= chunk_size:
                    self.db.executemany("""
                        INSERT INTO navigation_properties (
                            entity_type_id, name, target_entity_type, relationship_type,
                            is_collection, nullable, annotations
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, nav_props_batch)
                    nav_props_batch = []
        
        # Flush remaining
        if nav_props_batch:
            self.db.executemany("""
                INSERT INTO navigation_properties (
                    entity_type_id, name, target_entity_type, relationship_type,
                    is_collection, nullable, annotations
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, nav_props_batch)
            
        return total_nav_props
    
    async def _parse_enum_types(
        self,
        root: ET.Element, 
        chunk_size: int
    ) -> Dict[str, int]:
        """Parse enum type definitions"""
        
        enum_types_batch = []
        enum_type_map = {}
        
        for enum_type in root.findall(".//{http://docs.oasis-open.org/odata/ns/edm}EnumType"):
            name = enum_type.get("Name")
            if not name:
                continue
            
            underlying_type = enum_type.get("UnderlyingType", "Edm.Int32")
            is_flags = enum_type.get("IsFlags", "false").lower() == "true"
            namespace = "Microsoft.Dynamics.DataEntities"
            
            annotations = self._parse_annotations(enum_type)
            
            enum_types_batch.append((
                name, underlying_type, is_flags, namespace,
                json.dumps(annotations) if annotations else None
            ))
            
            if len(enum_types_batch) >= chunk_size:
                await self._flush_enum_types_batch(enum_types_batch, enum_type_map)
                enum_types_batch = []
        
        # Flush remaining
        if enum_types_batch:
            await self._flush_enum_types_batch(enum_types_batch, enum_type_map)
            
        return enum_type_map
    
    async def _flush_enum_types_batch(
        self,
        batch: List[Tuple],
        enum_type_map: Dict[str, int]
    ):
        """Bulk insert enum types and update mapping"""
        cursor = self.db.executemany("""
            INSERT INTO enum_types (name, underlying_type, is_flags, namespace, annotations)
            VALUES (?, ?, ?, ?, ?)
        """, batch)
        
        # Get IDs for mapping
        last_rowid = cursor.lastrowid
        if last_rowid is not None:
            start_id = last_rowid - len(batch) + 1
            for i, (name, *_) in enumerate(batch):
                enum_type_map[name] = start_id + i
        else:
            # Fallback: query for the IDs
            for name, *_ in batch:
                cursor = self.db.execute("SELECT id FROM enum_types WHERE name = ?", (name,))
                row = cursor.fetchone()
                if row:
                    enum_type_map[name] = row[0]
    
    async def _parse_enum_members(
        self,
        root: ET.Element,
        enum_type_map: Dict[str, int],
        chunk_size: int
    ) -> int:
        """Parse enum member definitions"""
        
        enum_members_batch = []
        total_members = 0
        
        for enum_type in root.findall(".//{http://docs.oasis-open.org/odata/ns/edm}EnumType"):
            enum_name = enum_type.get("Name")
            if not enum_name:
                continue
                
            enum_type_id = enum_type_map.get(enum_name)
            if not enum_type_id:
                continue
            
            ordinal = 0
            for member in enum_type.findall("./{http://docs.oasis-open.org/odata/ns/edm}Member"):
                member_name = member.get("Name")
                member_value = member.get("Value", "0")
                
                if not member_name:
                    continue
                
                annotations = self._parse_annotations(member)
                
                enum_members_batch.append((
                    enum_type_id, member_name, member_value,
                    json.dumps(annotations) if annotations else None,
                    ordinal
                ))
                
                ordinal += 1
                total_members += 1
                
                if len(enum_members_batch) >= chunk_size:
                    self.db.executemany("""
                        INSERT INTO enum_members (
                            enum_type_id, name, value, annotations, ordinal_position
                        ) VALUES (?, ?, ?, ?, ?)
                    """, enum_members_batch)
                    enum_members_batch = []
        
        # Flush remaining
        if enum_members_batch:
            self.db.executemany("""
                INSERT INTO enum_members (
                    enum_type_id, name, value, annotations, ordinal_position
                ) VALUES (?, ?, ?, ?, ?)
            """, enum_members_batch)
            
        return total_members
    
    async def _update_search_index(
        self,
        entity_set_map: Dict[str, Dict[str, Any]],
        enum_type_map: Dict[str, int]
    ):
        """Update FTS search index for fast text searching"""
        
        # Clear existing index
        self.db.execute("DELETE FROM entity_search")
        
        # Add entities to search index
        entity_search_batch = []
        for set_name, info in entity_set_map.items():
            entity_search_batch.append((
                set_name,
                "entity", 
                f"D365 entity: {info['entity_type_name']}"
            ))
        
        # Add enums to search index
        for enum_name in enum_type_map.keys():
            entity_search_batch.append((
                enum_name,
                "enum",
                f"D365 enum: {enum_name}"
            ))
        
        self.db.executemany("""
            INSERT INTO entity_search (name, type, description)
            VALUES (?, ?, ?)
        """, entity_search_batch)
    
    async def _record_sync_metadata(self, stats: Dict[str, Any]):
        """Record metadata sync statistics"""
        self.db.execute("""
            INSERT INTO metadata_sync (
                last_sync_at, last_sync_duration_ms, xml_size_bytes,
                entity_count, enum_count, sync_status, d365_instance
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            int(stats.get("total_duration_seconds", 0) * 1000),
            stats["xml_size_bytes"],
            stats["entity_types_parsed"],
            stats["enum_types_parsed"],
            "success",
            stats["d365_instance"]
        ))
    
    def _parse_annotations(self, element: ET.Element) -> Dict[str, Any]:
        """Parse OData annotations from an element"""
        annotations = {}
        
        # Look for annotation elements
        for annotation in element.findall(".//{http://docs.oasis-open.org/odata/ns/edm}Annotation"):
            term = annotation.get("Term")
            if term:
                # Simple annotation value
                value = annotation.get("String") or annotation.get("Bool") or annotation.get("Int")
                if value:
                    annotations[term] = value
        
        return annotations