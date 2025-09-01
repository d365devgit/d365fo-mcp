-- D365FO MCP Database Schema
-- This file documents the complete database schema for reference

-- Entity Instructions Table
-- Stores user-generated instructions for entity usage patterns
CREATE TABLE entity_instructions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT NOT NULL,
    operation_type TEXT NOT NULL CHECK (operation_type IN ('read', 'create', 'update', 'delete')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    example_query TEXT,
    example_data TEXT,
    tags TEXT,  -- JSON array
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'user'
);

-- Indexes for entity instructions
CREATE INDEX idx_instructions_entity_operation ON entity_instructions(entity_name, operation_type);
CREATE INDEX idx_instructions_success_rate ON entity_instructions(success_count DESC, failure_count ASC);
CREATE INDEX idx_instructions_created_at ON entity_instructions(created_at DESC);

-- Metadata Cache Table  
-- Caches D365 entity metadata to reduce API calls
CREATE TABLE metadata_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT NOT NULL UNIQUE,
    metadata TEXT NOT NULL,  -- JSON metadata
    relationships TEXT,      -- JSON relationships
    cached_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL
);

-- Indexes for metadata cache
CREATE INDEX idx_metadata_entity ON metadata_cache(entity_name);
CREATE INDEX idx_metadata_expires ON metadata_cache(expires_at);

-- Usage Statistics Table
-- Tracks tool usage for analytics and optimization
CREATE TABLE usage_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for usage stats
CREATE INDEX idx_usage_entity_operation ON usage_stats(entity_name, operation_type);
CREATE INDEX idx_usage_success ON usage_stats(success, created_at);
CREATE INDEX idx_usage_created_at ON usage_stats(created_at DESC);

-- Migration tracking table
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);