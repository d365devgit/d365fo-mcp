# D365FO MCP Server

A production-ready Model Context Protocol (MCP) server for Microsoft Dynamics 365 Finance & Operations with dependency injection architecture, automatic token refresh, and intelligent entity instructions that learn and improve over time.

## Features

🔍 **Smart Entity Discovery** - Comprehensive D365 entity and field discovery with relevance-scored search and pagination  
🔗 **Entity Relationships** - Navigation properties and relationship query guidance  
📋 **Advanced Enum Support** - Complete enum definitions with OData syntax generation and entity-specific enum field discovery  
⚡ **Robust Operations** - OData CRUD operations with automatic token refresh and intelligent company filtering  
🧠 **Learning System** - Save, merge, and reuse successful entity usage patterns with analytics  
🏗️ **Enterprise Architecture** - Dependency injection, repository pattern, factory pattern for extensibility  
🔐 **Production Authentication** - Automatic OAuth token refresh on expiration  
📱 **Local First** - SQLite storage, optimized queries, background sync capabilities  

## Quick Start

```bash
# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate     # On Windows

# Install dependencies
uv sync

# Configure D365 connection
cp .env.example .env
# Edit .env with your D365 credentials

# Run the MCP server
python -m d365fo_mcp.main

# Or install in Claude Desktop - see Configuration section
```

## Configuration

### Environment Variables

Create a `.env` file with your D365 credentials:

```bash
# D365 Authentication (Required)
AZURE_CLIENT_ID=<service-principal-client-id>
AZURE_CLIENT_SECRET=<service-principal-secret>
AZURE_TENANT_ID=<azure-tenant-id>
D365_BASE_URL=<d365-full-url>

# Optional Configuration
DATAAREAID=usmf                      # Default company ID
DATABASE_PATH=./data/d365fo-mcp.db   # SQLite database location (auto-created)
METADATA_CACHE_HOURS=24              # Metadata cache duration
LOG_LEVEL=info                       # Logging verbosity
DEBUG=false                          # Enable debug mode
SQLITE_ECHO=false                    # Echo SQLite queries to logs
```

### Claude Desktop Integration

Add to your Claude Desktop configuration (`~/Library/Application Support/Code/User/mcp.json`):

```json
{
  "mcpServers": {
    "D365FO MCP Server": {
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "d365fo_mcp.main"],
      "cwd": "/path/to/d365fo-mcp",
      "env": {
        "PYTHONPATH": "/path/to/d365fo-mcp",
        "AZURE_CLIENT_ID": "your-client-id",
        "AZURE_CLIENT_SECRET": "your-client-secret", 
        "AZURE_TENANT_ID": "your-tenant-id",
        "D365_BASE_URL": "https://your-env.sandbox.operations.dynamics.com",
        "DATAAREAID": "usmf",
        "DATABASE_PATH": "/absolute/path/to/d365fo-mcp/data/d365fo-mcp.db"
      }
    }
  }
}
```

⚠️ **Important**: Use absolute paths for `DATABASE_PATH` in Claude Desktop configuration.

## Usage Workflows

### 1. Entity Discovery with Relevance Search
```json
// Search for entities with intelligent relevance scoring
search_entities("Customer", limit=10, skip=0)
// Returns: exact matches first, then partial matches with relevance scores

// Get comprehensive entity metadata (REQUIRED before operations)
get_entity_metadata("CustomersV3") 
// Returns: field definitions, data types, required fields, enum fields

// Get specific field definitions 
get_entity_fields("CustomersV3")
// Returns: detailed field info with constraints and relationships
```

### 2. Advanced Enum Operations
```json
// Search for enums with pagination
search_enums("Status", limit=20, skip=0)

// Get enum with OData syntax generation
get_enum_metadata("CustVendorBlocked")
// Returns: enum values + exact OData syntax for filtering

// Find all enum fields in a specific entity
get_entity_enum_fields("CustomersV3")
// Returns: field names, enum types, and usage guidance
```

### 3. Robust Data Operations with Auto-Retry
```json
// Query with automatic token refresh on 401 errors
get_odata_entity("CustomersV3", 
    filter_query="CustomerGroupId eq 'RETAIL'",
    select_fields="CustomerAccount,CustomerName,CustomerGroupId",
    top=50,
    dataareaid="usmf"
)

// Use wildcard searches (D365 OData syntax)
get_odata_entity("LedgerJournalTransBiEntities",
    filter_query="LedgerDimensionValuesJson eq '*50111*' and TransDate ge 2025-07-01T00:00:00Z",
    top=100
)

// Create with proper field validation
create_odata_entity("CustomersV3", 
    data={
        "CustomerAccount": "CUST001",
        "CustomerName": "Test Customer",
        "CustomerGroupId": "RETAIL"
    },
    dataareaid="usmf"
)
```

### 4. Learning System with Merge Intelligence
```json
// Save successful patterns that merge with existing instructions
save_entity_instruction(
    entity_name="TrialBalanceFiscalYearSnapshots",
    operation_type="read", 
    instruction={
        "title": "Trial Balance Account Reconciliation",
        "description": "Query pattern for account reconciliations using DimensionValue1 for main accounts...",
        "example_query": "DimensionValue1 eq '50111' and PeriodEndDate ge 2025-07-01T00:00:00Z",
        "tags": ["trial-balance", "reconciliation", "financial-reporting"]
    },
    update_mode="merge"  // Intelligently combines with existing instructions
)

// Get learned patterns with success analytics
get_entity_instructions("TrialBalanceFiscalYearSnapshots", "read")
// Returns: instructions, success rates, usage patterns, examples
```

## Development

```bash
# Install development dependencies
uv sync --extra dev

# Run tests
pytest

# Format code
ruff format .

# Type check
mypy src/d365fo_mcp
```

## Architecture

**Core Framework:**
- **FastMCP 2.0** - Production MCP server framework with tool registry
- **Dependency Injection** - Repository, Service, and Factory patterns for extensibility
- **SQLite** - High-performance local storage with WAL mode and optimized indexes

**Authentication & Communication:**
- **Azure Identity** - Service principal authentication with automatic token refresh
- **HTTPX** - Async HTTP client with retry logic and timeout handling
- **Automatic Token Refresh** - Handles OAuth token expiration transparently

**Data Layer:**
- **Repository Pattern** - Pluggable storage backends (SQLite, future Supabase)
- **Optimized Queries** - Relevance scoring, pagination, full-text search
- **Background Sync** - Metadata caching with intelligent refresh strategies

**Business Logic:**
- **Service Layer** - Clean separation between tools and data access
- **Instruction Learning** - Pattern recognition and success analytics
- **Company Context** - Intelligent multi-company operation handling

See [APPROACH.md](APPROACH.md) for detailed architectural decisions and technical approach.

## License

MIT License - see LICENSE file for details.