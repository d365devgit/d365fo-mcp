"""
SQLite Schema Definitions

Contains all table creation SQL and migrations for SQLite implementation.
"""

from typing import Dict, Any

# Migration for enhanced metadata storage schema
METADATA_STORAGE_MIGRATION = {
    "version": 4,
    "description": "Optimized metadata storage schema",
    "sql": """
        -- Raw metadata cache table (for backward compatibility)
        CREATE TABLE IF NOT EXISTS raw_metadata_cache (
            id INTEGER PRIMARY KEY,
            metadata_xml TEXT NOT NULL,
            cached_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL
        );
        
        -- Simple metadata cache table (current implementation)
        CREATE TABLE IF NOT EXISTS metadata_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_name TEXT NOT NULL UNIQUE,
            metadata TEXT NOT NULL,  -- JSON metadata
            cached_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL
        );
        
        -- Usage statistics table
        CREATE TABLE IF NOT EXISTS usage_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation TEXT NOT NULL,
            entity_name TEXT,
            success BOOLEAN NOT NULL,
            execution_time_ms INTEGER,
            metadata TEXT,  -- JSON metadata
            recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Instruction usage statistics table
        CREATE TABLE IF NOT EXISTS instruction_usage_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instruction_id TEXT NOT NULL,
            success BOOLEAN NOT NULL,
            feedback_score INTEGER,
            metadata TEXT,  -- JSON metadata
            recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_metadata_entity ON metadata_cache(entity_name);
        CREATE INDEX IF NOT EXISTS idx_metadata_expires ON metadata_cache(expires_at);
        CREATE INDEX IF NOT EXISTS idx_usage_operation ON usage_stats(operation, recorded_at);
        CREATE INDEX IF NOT EXISTS idx_usage_entity ON usage_stats(entity_name, recorded_at);
        CREATE INDEX IF NOT EXISTS idx_instruction_usage ON instruction_usage_stats(instruction_id, recorded_at);
    """
}

# Migration definitions for SQLite
SQLITE_MIGRATIONS = [
    {
        "version": 1,
        "description": "Initial schema - entity instructions and metadata cache",
        "sql": """
            -- Entity Instructions Table
            CREATE TABLE IF NOT EXISTS entity_instructions (
                id TEXT PRIMARY KEY,  -- UUID
                entity_name TEXT NOT NULL,
                operation_type TEXT NOT NULL CHECK (operation_type IN ('read', 'create', 'update', 'delete')),
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                example_query TEXT,
                example_data TEXT,  -- JSON data
                tags TEXT,  -- JSON array
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT
            );
            
            -- Indexes for entity instructions
            CREATE INDEX IF NOT EXISTS idx_instructions_entity_operation 
                ON entity_instructions(entity_name, operation_type);
            CREATE INDEX IF NOT EXISTS idx_instructions_created_at 
                ON entity_instructions(created_at DESC);
                
            -- Migration tracking table
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """,
    },
    {
        "version": 2,
        "description": "Add normalized metadata tables for bulk operations",
        "sql": """
            -- Entity Types Table
            CREATE TABLE IF NOT EXISTS entity_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                base_type TEXT,
                abstract BOOLEAN DEFAULT FALSE,
                has_key BOOLEAN DEFAULT FALSE,
                namespace TEXT,
                annotations TEXT  -- JSON
            );
            
            -- Entity Sets Table
            CREATE TABLE IF NOT EXISTS entity_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                entity_type_id INTEGER NOT NULL,
                annotations TEXT,  -- JSON
                FOREIGN KEY (entity_type_id) REFERENCES entity_types(id)
            );
            
            -- Entity Properties Table
            CREATE TABLE IF NOT EXISTS entity_properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                nullable BOOLEAN DEFAULT TRUE,
                max_length INTEGER,
                precision INTEGER,
                scale INTEGER,
                is_key BOOLEAN DEFAULT FALSE,
                annotations TEXT,  -- JSON
                FOREIGN KEY (entity_type_id) REFERENCES entity_types(id)
            );
            
            -- Navigation Properties Table
            CREATE TABLE IF NOT EXISTS navigation_properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                target_entity_type TEXT,
                relationship_type TEXT,
                is_collection BOOLEAN DEFAULT FALSE,
                nullable BOOLEAN DEFAULT TRUE,
                annotations TEXT,  -- JSON
                FOREIGN KEY (entity_type_id) REFERENCES entity_types(id)
            );
            
            -- Enum Types Table
            CREATE TABLE IF NOT EXISTS enum_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                underlying_type TEXT,
                is_flags BOOLEAN DEFAULT FALSE,
                namespace TEXT,
                annotations TEXT  -- JSON
            );
            
            -- Enum Members Table
            CREATE TABLE IF NOT EXISTS enum_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enum_type_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                value TEXT NOT NULL,
                annotations TEXT,  -- JSON
                ordinal_position INTEGER,
                FOREIGN KEY (enum_type_id) REFERENCES enum_types(id)
            );
            
            -- Entity Search Table for full-text search
            CREATE TABLE IF NOT EXISTS entity_search (
                name TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                description TEXT
            );
            
            -- Metadata Sync Tracking Table
            CREATE TABLE IF NOT EXISTS metadata_sync (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                last_sync_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_sync_duration_ms INTEGER,
                xml_size_bytes INTEGER,
                entity_types_parsed INTEGER DEFAULT 0,
                enum_types_parsed INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending'
            );
            
            -- Indexes for performance
            CREATE INDEX IF NOT EXISTS idx_entity_types_name ON entity_types(name);
            CREATE INDEX IF NOT EXISTS idx_entity_sets_name ON entity_sets(name);
            CREATE INDEX IF NOT EXISTS idx_entity_sets_type ON entity_sets(entity_type_id);
            CREATE INDEX IF NOT EXISTS idx_entity_properties_entity ON entity_properties(entity_type_id);
            CREATE INDEX IF NOT EXISTS idx_entity_properties_name ON entity_properties(entity_type_id, name);
            CREATE INDEX IF NOT EXISTS idx_navigation_properties_entity ON navigation_properties(entity_type_id);
            CREATE INDEX IF NOT EXISTS idx_enum_types_name ON enum_types(name);
            CREATE INDEX IF NOT EXISTS idx_enum_members_enum ON enum_members(enum_type_id);
            CREATE INDEX IF NOT EXISTS idx_entity_search_name ON entity_search(name);
        """,
    },
    {
        "version": 3,
        "description": "Add unique constraint for entity+operation instructions",
        "sql": """
            -- Remove existing index
            DROP INDEX IF EXISTS idx_instructions_entity_operation;
            
            -- Create temporary table to handle duplicates
            CREATE TEMPORARY TABLE temp_instructions AS
            SELECT id, entity_name, operation_type, title, description, 
                   example_query, example_data, tags, success_count, failure_count,
                   created_at, updated_at, created_by,
                   ROW_NUMBER() OVER (PARTITION BY entity_name, operation_type 
                                      ORDER BY success_count DESC, created_at DESC) as rn
            FROM entity_instructions;
            
            -- Delete all records from original table
            DELETE FROM entity_instructions;
            
            -- Insert back only the best record for each entity+operation combination
            INSERT INTO entity_instructions (id, entity_name, operation_type, title, description,
                                           example_query, example_data, tags, success_count, failure_count,
                                           created_at, updated_at, created_by)
            SELECT id, entity_name, operation_type, title, description,
                   example_query, example_data, tags, success_count, failure_count,
                   created_at, updated_at, created_by
            FROM temp_instructions 
            WHERE rn = 1;
            
            -- Create unique index
            CREATE UNIQUE INDEX idx_instructions_entity_operation_unique 
                ON entity_instructions(entity_name, operation_type);
        """,
    },
    METADATA_STORAGE_MIGRATION,
]

# Performance-optimized queries for common operations
OPTIMIZED_QUERIES = {
    "search_entities": """
        SELECT entity_name, 
               json_extract(metadata, '$.description') as description,
               json_extract(metadata, '$.entity_type') as entity_type,
               json_extract(metadata, '$.use_for_queries') as use_for_queries,
               (CASE 
                   WHEN lower(entity_name) = lower(?) THEN 100
                   WHEN lower(entity_name) LIKE lower(?) || '%' THEN 50
                   WHEN lower(entity_name) LIKE '%' || lower(?) || '%' THEN 25
                   WHEN json_extract(metadata, '$.description') LIKE '%' || ? || '%' THEN 10
                   ELSE 0
               END) as relevance
        FROM metadata_cache
        WHERE relevance > 0 AND expires_at > ?
        ORDER BY relevance DESC, entity_name ASC
        LIMIT ? OFFSET ?
    """,
    
    "get_entity_metadata": """
        SELECT entity_name, metadata, cached_at
        FROM metadata_cache 
        WHERE entity_name = ? AND expires_at > ?
    """,
    
    "list_cached_entities": """
        SELECT entity_name, cached_at, expires_at,
               json_extract(metadata, '$.description') as description,
               json_extract(metadata, '$.entity_type') as entity_type
        FROM metadata_cache 
        WHERE expires_at > ?
        ORDER BY entity_name
    """,
    
    "get_usage_stats": """
        SELECT operation, entity_name, success, execution_time_ms, metadata, recorded_at
        FROM usage_stats 
        WHERE recorded_at > ?
        ORDER BY recorded_at DESC
        LIMIT 100
    """
}

def get_sqlite_performance_tips() -> Dict[str, Any]:
    """Performance optimization tips for SQLite implementation"""
    return {
        "schema_design": [
            "JSON columns for flexible metadata storage",
            "Strategic indexes on common query patterns", 
            "UUID primary keys for distributed scenarios",
            "Proper foreign key constraints"
        ],
        "query_optimization": [
            "JSON extract functions for metadata queries",
            "Relevance scoring for better search results",
            "Time-based filtering with indexed timestamps",
            "Efficient pagination with LIMIT/OFFSET"
        ],
        "expected_performance": [
            "Entity search: <2ms for most queries",
            "Metadata retrieval: <1ms",
            "Usage stats: <5ms",
            "Instruction operations: <3ms"
        ],
        "storage_estimates": [
            "Metadata cache: ~10-50MB depending on entity count",
            "Instructions: ~1-10MB depending on usage",
            "Usage stats: ~1MB per month",
            "Total: Usually under 100MB"
        ]
    }
