# D365FO MCP Server - Architectural Approach

## Overview

The D365 Finance & Operations MCP (Model Context Protocol) Server provides AI-powered assistance for D365FO development through a clean, dependency injection-based architecture. This document explains the key architectural decisions and approach taken.

## Core Architectural Principles

### 1. **Dependency Injection First**
The entire system is built around a central `DIContainer` that manages all dependencies:
- **No tight coupling** between components
- **Testable** - easy to mock dependencies for testing  
- **Configurable** - swap implementations (SQLite ↔ Supabase) via configuration
- **Lifecycle management** - proper initialization and cleanup

### 2. **Interface-Based Design**
Every major component has a well-defined interface:
```
IMetadataRepository → SQLiteMetadataRepository | SupabaseMetadataRepository
IAuthProvider      → AzureAuthProvider       | OktaAuthProvider  
ID365Client        → D365Client              | MockD365Client
```
This enables multiple implementations and easy testing.

### 3. **Implementation-Specific Organization**
Instead of mixing implementation details, we separate by backend:
```
repositories/
├── metadata/interface.py        # Abstract interface
├── instructions/interface.py    # Abstract interface  
├── sqlite/                      # SQLite-specific implementation
│   ├── database.py
│   ├── metadata_repository.py
│   ├── bulk_parser.py
│   └── migrations.py
└── supabase/                    # Future Supabase implementation
    ├── client.py
    └── metadata_repository.py
```

## Key Design Decisions

### 1. **Repository Pattern with Clear Separation**
**Problem**: Original code mixed database logic with business logic  
**Solution**: Clean repository layer with implementation-specific folders
- **Business logic** stays in service layer
- **Data access** encapsulated in repositories  
- **Database specifics** contained in implementation folders

### 2. **High-Performance Metadata Processing**
**Problem**: D365FO metadata XML files are huge (46MB+)  
**Solution**: Specialized bulk parser with performance optimizations
- **Chunked processing** (1000 records/batch)
- **SQLite optimizations** (WAL mode, large cache, indexes)
- **Background sync** with intelligent scheduling
- **7-phase parsing pipeline** for efficiency

### 3. **Factory Pattern for Configuration-Driven Creation**
**Problem**: Complex object construction with multiple dependencies  
**Solution**: Dedicated factories for each component type
```python
# Configuration drives implementation choice
metadata_repository: "sqlite"     # or "supabase"
auth_provider: "azure"           # or "okta" 
d365_client: "http"              # or "mock"

# Factories handle complexity
RepositoryFactory.create_metadata_repository(settings)
AuthProviderFactory.create(settings)  
ClientFactory.create(settings, auth_provider)
```

### 4. **Service Layer for Business Logic**
**Problem**: MCP tools were directly calling repositories  
**Solution**: Service layer provides business logic and coordinates operations
- **MetadataService**: Entity discovery, caching, search optimization
- **InstructionsService**: AI instruction management and analytics
- **BackgroundMetadataSync**: Automated metadata refresh

### 5. **Production Authentication with Auto-Refresh**
**Problem**: OAuth tokens expire causing 401 errors during long-running sessions  
**Solution**: Intelligent token management with transparent refresh
- **Token Cache**: In-memory caching with expiration tracking
- **Automatic Retry**: 401 errors trigger token refresh and request retry
- **Service Principal**: Uses Azure Client Credentials flow for reliability
- **Request Interception**: All HTTP calls go through authenticated request wrapper

## Architecture Benefits

### ✅ **Extensibility**
- Add new repository backends (Supabase, CosmosDB) without changing existing code
- New authentication providers via simple interface implementation
- Plugin architecture for custom functionality

### ✅ **Testability**  
- Every component can be tested in isolation with mocks
- Integration tests with real databases
- Performance tests with large datasets

### ✅ **Performance**
- Background metadata sync keeps responses fast
- Optimized SQLite queries with relevance scoring
- Efficient bulk processing of large XML files
- Automatic token refresh prevents authentication delays

### ✅ **Production Reliability**
- Handles OAuth token expiration transparently
- Retry logic with exponential backoff
- Comprehensive error handling and logging
- Path resolution works in different deployment contexts

### ✅ **Maintainability**
- Clear separation of concerns across layers
- Configuration-driven behavior reduces code changes
- Consistent patterns across all components

## Implementation Highlights

### **Circular Import Resolution**
**Problem**: Repository interfaces and implementations had circular dependencies  
**Solution**: Clean import hierarchy
```python
# interfaces/ exports only abstractions
from .interface import IMetadataRepository

# sqlite/ imports interfaces, not vice versa  
from ..metadata import IMetadataRepository

# factories/ import concrete implementations directly
from ..repositories.sqlite import SQLiteMetadataRepository
```

### **Background Processing Architecture**
**Problem**: Metadata sync shouldn't block user requests  
**Solution**: Optional background service with intelligent scheduling
- **Async task management** with proper shutdown
- **Retry logic** with exponential backoff
- **Callback system** for sync notifications
- **Availability waiting** when metadata not ready

### **Configuration Management**
**Problem**: Multiple ways to configure led to confusion  
**Solution**: Unified Settings class with priority hierarchy
```
Environment Variables (highest priority)
↓
Configuration Files  
↓
Command Line Arguments
↓ 
Default Values (lowest priority)
```

## Folder Structure Logic

```
src/d365fo_mcp/
├── config.py                   # Unified configuration
├── di_container.py              # Central dependency management
├── factories/                   # Object creation patterns
├── auth/                        # Authentication abstractions + implementations
├── client/                      # D365FO client abstractions + implementations  
├── repositories/                # Data access layer
│   ├── metadata/interface.py    # Abstract repository contracts
│   ├── instructions/interface.py
│   ├── sqlite/                  # SQLite implementation
│   └── supabase/                # Future cloud implementation
├── services/                    # Business logic layer
│   ├── metadata/                # Entity discovery and caching
│   └── instructions/            # AI instruction management
└── tools/                       # MCP protocol implementation
```

## What This Architecture Enables

1. **Multiple Backend Support**: Easy to add Supabase, CosmosDB, or other backends
2. **Environment Flexibility**: Same code works in dev, staging, production with just config changes
3. **Performance Scaling**: Background sync, caching, and optimized queries handle large D365FO environments  
4. **Testing Confidence**: Comprehensive test coverage with proper mocking
5. **Team Development**: Clear boundaries make it easy for multiple developers to work simultaneously
6. **Future Extensions**: Plugin architecture supports custom functionality without core changes

## Why This Approach?

The original architecture was functional but had several limitations:
- **Tight coupling** made testing and extension difficult
- **Mixed concerns** put database logic alongside business logic  
- **No clear patterns** for adding new backends or authentication methods
- **Performance issues** with large metadata files and frequent queries

The new dependency injection approach addresses all these concerns while maintaining the same external MCP interface. The result is a production-ready, extensible foundation that can grow with your D365FO integration needs.