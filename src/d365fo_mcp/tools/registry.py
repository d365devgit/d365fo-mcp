"""
Tool Registry for D365FO MCP Server

Centralized tool registration with consistent patterns and comprehensive guidance.
"""

import json
from typing import Dict, Any, Optional
from fastmcp import FastMCP
from fastmcp.exceptions import FastMCPError
import structlog

from ..services.metadata import IMetadataService
from ..services.instructions import IInstructionsService
from ..client import ID365Client

logger = structlog.get_logger(__name__)


class ToolRegistry:
    """
    Centralized tool registration with consistent patterns and comprehensive guidance.
    """
    
    @staticmethod
    def register_all_tools(
        mcp: FastMCP,
        metadata_service: IMetadataService,
        d365_client: ID365Client, 
        instructions_service: IInstructionsService
    ) -> None:
        """Register all MCP tools with comprehensive guidance"""
        logger.info("Registering MCP tools with comprehensive guidance")
        
        # Register metadata tools
        ToolRegistry._register_metadata_tools(mcp, metadata_service)
        
        # Register base operation tools
        ToolRegistry._register_base_operation_tools(mcp, d365_client, instructions_service)
        
        # Register instruction tools
        ToolRegistry._register_instruction_tools(mcp, instructions_service)
        
        logger.info("All MCP tools registered successfully")
    
    @staticmethod
    def _register_metadata_tools(mcp: FastMCP, metadata_service: IMetadataService) -> None:
        """Register metadata discovery tools"""
        
        @mcp.tool
        async def search_entities(pattern: str, limit: int = 20, skip: int = 0) -> str:
            """
            Search for D365 entities by name pattern.

            MANDATORY PRECONDITIONS - DO NOT SKIP:
            1. This is the FIRST tool to use when exploring D365 data
            2. Use exact entity names from results in all subsequent calls
            3. NEVER guess entity names - always search first

            CRITICAL RULES:
            - Use the 'use_for_queries' field from results (not 'name') 
            - Entity names are case-sensitive and exact
            - Save entity names for metadata lookup and data queries

            Args:
                pattern: Search term (Customer, Journal, Ledger, etc.)
                limit: Max results (default 20, max 100)
                skip: Skip records for pagination

            Next steps after search:
                1. get_entity_metadata(entity_name) - get field definitions
                2. get_odata_entity(entity_name) - query the data
            """
            try:
                results = await metadata_service.search_entities(pattern, min(limit, 100), skip)
                return json.dumps({"entities": results, "pattern": pattern, "total": len(results)}, indent=2)
            except Exception as e:
                logger.error("Entity search failed", error=str(e))
                raise FastMCPError(f"Failed to search entities: {e}")

        @mcp.tool
        async def get_entity_metadata(entity_name: str) -> str:
            """
            Get complete entity metadata including field definitions.

            MANDATORY PRECONDITIONS - DO NOT SKIP:
            1. Get entity_name from search_entities() - NEVER guess names
            2. This tool is REQUIRED before any data operations
            3. Use EXACT field names from results in all queries

            CRITICAL USAGE:
            - Check 'dataareaid' field exists before using company filtering
            - Use exact field names (case-sensitive) in queries
            - Required fields must be included in create operations
            - Check field types before setting values

            Args:
                entity_name: EXACT name from search_entities results

            Returns metadata with:
                - fields: All field definitions with names/types
                - keys: Primary and foreign keys
                - navigation: Related entities
            """
            try:
                metadata = await metadata_service.get_entity_metadata(entity_name)
                if not metadata:
                    raise FastMCPError(f"Entity '{entity_name}' not found")
                return json.dumps(metadata, indent=2, default=str)
            except Exception as e:
                logger.error("Get entity metadata failed", error=str(e))
                raise FastMCPError(f"Failed to get metadata for {entity_name}: {e}")

        @mcp.tool
        async def list_all_entities() -> str:
            """
            List all available D365 entities.

            Returns complete inventory of entities available for queries.
            Use search_entities with patterns for more targeted discovery.

            Returns:
                JSON with all entity names, descriptions, and basic metadata

            Example:
                list_all_entities()
            """
            try:
                entities = await metadata_service.list_all_entities()
                return json.dumps({"entities": entities, "total_count": len(entities)}, indent=2)
            except Exception as e:
                logger.error("List entities failed", error=str(e))
                raise FastMCPError(f"Failed to list entities: {e}")

        @mcp.tool
        async def get_entity_fields(entity_name: str) -> str:
            """
            Get detailed field definitions for entity.

            MANDATORY PRECONDITIONS - DO NOT SKIP:
            1. Get entity_name from search_entities() first
            2. Use EXACT field names from results - NO guessing
            3. Check field types before setting values

            FIELD USAGE RULES:
            - Field names are case-sensitive and exact
            - Required fields must be included in creates
            - Check enum fields need get_enum_metadata()
            - Validate data types match field definitions

            Args:
                entity_name: EXACT name from search_entities

            Returns field details:
                - Field names (exact spelling)
                - Data types (string, number, boolean, date)
                - Required vs optional fields
                - Enum fields needing value lookup
            """
            try:
                fields = await metadata_service.get_entity_fields(entity_name)
                return json.dumps({"entity": entity_name, "fields": fields}, indent=2)
            except Exception as e:
                logger.error("Get entity fields failed", error=str(e))
                raise FastMCPError(f"Failed to get fields for {entity_name}: {e}")

        @mcp.tool
        async def search_enums(pattern: str, limit: int = 20, skip: int = 0) -> str:
            """
            Search for D365 enums by name pattern.

            Use this tool to discover available enums and their names.
            Follow up with get_enum_metadata to get the specific values.

            Args:
                pattern: Search term (e.g., "NoYes", "Status", "Type")
                limit: Maximum results to return (default: 20, max: 100)
                skip: Number of results to skip for pagination (default: 0)

            Returns:
                JSON with matching enum names ordered by relevance

            Examples:
                search_enums("Status")
                search_enums("NoYes")  
                search_enums("Type", limit=50)
            """
            try:
                results = await metadata_service.search_enums(pattern, min(limit, 100), skip)
                if isinstance(results, dict):
                    # New repository format with pagination info
                    return json.dumps(results, indent=2)
                else:
                    # Legacy format - return as simple list
                    return json.dumps({"enums": results, "pattern": pattern, "total": len(results)}, indent=2)
            except Exception as e:
                logger.error("Enum search failed", error=str(e))
                raise FastMCPError(f"Failed to search enums: {e}")

        @mcp.tool
        async def get_enum_metadata(enum_name: str) -> str:
            """
            Get complete enum definition with all valid values and OData syntax.

            This is the key tool for getting enum possible values! Returns all enum members
            with their names, values, and proper OData filter syntax for each option.

            Args:
                enum_name: Exact enum name (case-sensitive, e.g., 'NoYes', 'LedgerJournalACType')

            Returns:
                JSON with complete enum metadata including:
                - All enum members with names and values
                - Proper OData filter syntax for each member  
                - Usage examples for filtering
                - Member count and annotations

            Examples:
                get_enum_metadata("NoYes")
                get_enum_metadata("LedgerJournalACType")
                get_enum_metadata("CurrentOperationsTax")

            Common enums:
                - NoYes (Yes/No boolean values)
                - LedgerJournalACType (Account types)
                - CurrentOperationsTax (Tax operations)
                - DimensionHierarchyType (Hierarchy types)
            """
            try:
                enum_data = await metadata_service.get_enum_metadata(enum_name)
                if not enum_data:
                    # Try to find similar enums to suggest
                    similar = await metadata_service.search_enums(enum_name, limit=5)
                    similar_list = similar.get("enums", similar) if isinstance(similar, dict) else similar
                    
                    if similar_list:
                        suggestion = f"Enum '{enum_name}' not found. Similar enums: {', '.join(similar_list[:5])}"
                    else:
                        suggestion = f"Enum '{enum_name}' not found. Use search_enums to find available enums."
                    
                    return json.dumps({
                        "error": "Enum not found",
                        "enum_name": enum_name,
                        "suggestion": suggestion
                    }, indent=2)

                # Format response for better usability
                formatted_response = {
                    "enum_name": enum_data["name"],
                    "member_count": enum_data.get("member_count", len(enum_data.get("members", []))),
                    "members": [],
                    "usage_examples": [],
                    "odata_filter_examples": [],
                    "annotations": enum_data.get("annotations", {})
                }

                # Process members with usage guidance
                members = enum_data.get("members", [])
                for member in members:
                    formatted_member = {
                        "name": member.get("name"),
                        "value": member.get("value"),
                        "odata_syntax": member.get("odata_syntax"),
                        "description": member.get("annotations", {}).get("description", "")
                    }

                    formatted_response["members"].append(formatted_member)

                    # Add practical usage examples
                    if member.get("odata_syntax"):
                        odata_syntax = member.get("odata_syntax")
                        filter_example = f"FieldName eq {odata_syntax}"
                        formatted_response["odata_filter_examples"].append({
                            "member": member.get("name"),
                            "filter_syntax": filter_example,
                            "description": f"Filter where field equals {member.get('name')}"
                        })

                # Add general usage guidance
                formatted_response["usage_guidance"] = {
                    "filter_pattern": f"FieldName eq Microsoft.Dynamics.DataEntities.{enum_name}'MemberName'",
                    "example_entity_query": f"get_odata_entity('EntityName', filter_query=\"EnumField eq Microsoft.Dynamics.DataEntities.{enum_name}'MemberValue'\")",
                    "note": "Replace 'FieldName', 'EntityName', 'EnumField', and 'MemberValue' with actual values from your use case"
                }

                return json.dumps(formatted_response, indent=2)
            except Exception as e:
                logger.error("Get enum metadata failed", error=str(e))
                raise FastMCPError(f"Failed to get enum metadata for {enum_name}: {e}")

        @mcp.tool
        async def get_entity_enum_fields(entity_name: str) -> str:
            """
            Get all enum fields for a specific entity with their enum types.

            Use this to quickly identify which fields in an entity are enums
            and what enum types they use. Follow up with get_enum_metadata 
            to get the possible values for each enum field.

            Args:
                entity_name: Target entity name

            Returns:
                JSON mapping of field names to enum information including:
                - enum_name: The D365 enum type name
                - odata_syntax: Proper OData reference syntax
                - usage_tip: How to use in filters

            Examples:
                get_entity_enum_fields("LedgerJournalHeaders")
                get_entity_enum_fields("CustomersV3")

            Workflow:
                1. get_entity_enum_fields("EntityName") - find enum fields
                2. get_enum_metadata("EnumTypeName") - get possible values
                3. Use values in get_odata_entity filters
            """
            try:
                enum_fields = await metadata_service.get_entity_enum_fields(entity_name)
                
                if not enum_fields:
                    # Check if entity exists
                    entity_data = await metadata_service.get_entity_metadata(entity_name)
                    if not entity_data:
                        return json.dumps({
                            "error": "Entity not found", 
                            "entity_name": entity_name,
                            "suggestion": f"Use search_entities('{entity_name}') to find similar entities"
                        }, indent=2)
                    else:
                        return json.dumps({
                            "entity_name": entity_name,
                            "enum_fields": {},
                            "message": "No enum fields found in this entity",
                            "suggestion": "Use get_entity_metadata to see all fields"
                        }, indent=2)

                # Enhanced response with usage guidance
                response = {
                    "entity_name": entity_name,
                    "enum_field_count": len(enum_fields),
                    "enum_fields": enum_fields,
                    "usage_guidance": {
                        "next_step": "Use get_enum_metadata('EnumName') to get possible values for each enum field",
                        "filter_example": "get_odata_entity('EntityName', filter_query=\"EnumFieldName eq Microsoft.Dynamics.DataEntities.EnumType'Value'\")",
                        "workflow": [
                            "1. Use get_enum_metadata() on the enum_name to see all possible values",
                            "2. Use the odata_syntax from enum metadata in your filters",
                            "3. Test with a small query first to verify the syntax"
                        ]
                    }
                }

                return json.dumps(response, indent=2)
            except Exception as e:
                logger.error("Get entity enum fields failed", error=str(e))
                raise FastMCPError(f"Failed to get enum fields for {entity_name}: {e}")
    
    @staticmethod
    def _register_base_operation_tools(
        mcp: FastMCP, 
        d365_client: ID365Client, 
        instructions_service: IInstructionsService
    ) -> None:
        """Register base CRUD operation tools with comprehensive guidance"""
        
        @mcp.tool
        async def get_odata_entity(
            entity_name: str,
            filter_query: Optional[str] = None,
            select_fields: Optional[str] = None,
            top: Optional[int] = None,
            skip: Optional[int] = None,
            orderby: Optional[str] = None,
            count: bool = False,
            dataareaid: Optional[str] = None,
        ) -> str:
            """
            Execute OData GET query against D365 entity with comprehensive guidance.

            IMPORTANT: Always check get_entity_instructions(entity_name, "read") first
            for proven patterns and examples before querying unfamiliar entities.

            ## Metadata Discovery Workflow:
            1. **Unknown Entity**: Use get_entity_metadata(entity_name) first
            2. **Check Instructions**: get_entity_instructions(entity_name, "read")
            3. **Explore Structure**: Review fields, keys, relationships
            4. **Start Simple**: Basic query with top=5
            5. **Add Filters**: Build complexity incrementally
            6. **Optimize**: Add select_fields and proper paging

            ## Company Filtering Strategy:

            ### When to use dataareaid:
            - **Use get_entity_metadata(entity_name) first** to check if dataareaid is available in an entity
            - **Transactional entities**: Usually require company specification (Customers, Sales Orders, etc.)
            - **Multi-company environments**: Always specify for company-specific data

            ### When NOT to use dataareaid:
            - **Master/Reference data**: Currencies, Countries, System Parameters
            - **Global configuration**: NumberSequences, System settings
            - **If entity doesn't support it**: Check metadata first to avoid errors

            ### Common Patterns:
            - **Current company**: Use default (omit dataareaid) for user's active company
            - **Specific company**: dataareaid=\"USMF\" for explicit company targeting
            - **Check entity support**: Always verify dataareaid field exists before using

            ## CRITICAL OData Syntax for D365:

            ### Wildcard vs Contains (MOST IMPORTANT):
            - ✅ **USE**: `filter_query=\"LedgerAccount eq '*50112*'\"` (WORKS)
            - ❌ **AVOID**: `contains(LedgerAccount, '50112')` (FAILS in D365)
            - ❌ **AVOID**: `substringof()` - Not supported in D365 OData
            - ✅ **For exact matches**: `MainAccountId eq '50112'`
            - ✅ **For text searches**: `Text eq '*INVOICE_NUMBER*'` or `Text eq '*VENDOR_NAME*'`

            ### Account Number Filtering Best Practices:
            - MainAccountId: Use exact match `eq '50112'`
            - LedgerAccount (with dimensions): Use wildcard `eq '*50112*'`
            - Always try wildcard first if exact match returns no results

            ## Paging Strategy Guide:

            ### Large Dataset Exploration (>1000 records):
            - Start: top=10, skip=0 (quick sample)
            - Count: count=true (get total records) 
            - Batch: top=100, skip=0,100,200... (efficient chunks)
            - Example: top=10, count=true → \"Total: 50,000 records\"

            ### Targeted Queries (<1000 records):
            - Filter first: filter_query=\"Status eq 'Active'\"
            - Then paginate: top=50 for manageable results
            - Sort for consistency: orderby=\"CreatedDate desc\"

            ### Performance Optimization:
            - Always use select_fields to limit data: select_fields=\"Name,Status,CreatedDate\"
            - Combine filter + select for best performance
            - Use orderby with paging for consistent results

            Args:
                entity_name: D365 entity name (use get_entity_metadata first for unfamiliar entities)
                filter_query: OData filter (e.g., \"Status eq 'Active' and CreatedDate gt 2024-01-01T00:00:00Z\")
                select_fields: Comma-separated fields (e.g., \"Name,Status,CreatedDate\") - improves performance
                top: Maximum records to return (default: 1000, max: 5000 for performance)
                skip: Records to skip for pagination (use with orderby for consistency)
                orderby: Sort expression (e.g., \"CreatedDate desc\" or \"Name asc,Status desc\")
                count: Include total count in response (useful for paging calculations)
                dataareaid: Company code (USMF, FRRT, etc.) - see company strategy above

            Returns:
                JSON response with entity data, metadata, and paging information

            Examples:
                # Basic exploration
                get_odata_entity(\"CustomersV3\", top=10, count=true)
                
                # Targeted query with company filter
                get_odata_entity(\"SalesOrderHeaders\", 
                               filter_query=\"Status eq 'Confirmed'\", 
                               dataareaid=\"USMF\", 
                               top=50)
                
                # Performance optimized
                get_odata_entity(\"LedgerTransactions\",
                               select_fields=\"AccountNum,Amount,TransDate\",
                               filter_query=\"TransDate gt 2024-01-01T00:00:00Z\",
                               orderby=\"TransDate desc\",
                               top=100)
                
                # Paging through large dataset  
                get_odata_entity(\"InventTransactions\", top=100, skip=200, orderby=\"ItemId\")

            Common Pitfalls to Avoid:
                ❌ Large queries without top limit (causes timeouts)
                ❌ Not paging through results to find the full set of options when searching for something
                ❌ Paging without orderby (inconsistent results)
                ❌ Making up field names in select_fields (causes errors)
                ❌ Trying to query by dataareaid on an entity that does not support it (causes errors)
                ❌ No select_fields on large entities (slow performance)
                ❌ Wrong dataareaid for master data (empty results)
                ❌ Skipping get_entity_instructions() (missing proven patterns)
                ❌ Using contains() instead of eq '*pattern*' for wildcard searches
            """
            try:
                # Build OData query string
                query_params = []
                if filter_query:
                    query_params.append(f"$filter={filter_query}")
                if select_fields:
                    query_params.append(f"$select={select_fields}")
                if top is not None:
                    query_params.append(f"$top={top}")
                if skip is not None:
                    query_params.append(f"$skip={skip}")
                if orderby:
                    query_params.append(f"$orderby={orderby}")
                if count:
                    query_params.append(f"$count=true")
                # If dataareaid is provided and not already in filter, add to filter
                if dataareaid:
                    # If $filter already exists, append with and, else create
                    if filter_query:
                        if f"dataAreaId eq '{dataareaid}'" not in filter_query:
                            # Add to filter
                            new_filter = f"({filter_query}) and dataAreaId eq '{dataareaid}'"
                            query_params[0] = f"$filter={new_filter}"
                    else:
                        query_params.append(f"$filter=dataAreaId eq '{dataareaid}'")

                query_str = "&".join(query_params)

                result = await d365_client.get_odata_entity(entity_name, query_str)

                return json.dumps(result, indent=2, default=str)
            except Exception as e:
                logger.error("OData entity query failed", error=str(e))
                raise FastMCPError(f"Failed to query {entity_name}: {e}")

        @mcp.tool
        async def create_odata_entity(
            entity_name: str,
            data: Dict[str, Any],
            dataareaid: Optional[str] = None,
        ) -> str:
            """
            Create new D365 entity record.

            MANDATORY PRECONDITIONS - DO NOT SKIP:
            1. ALWAYS call get_entity_metadata(entity_name) first 
            2. Use EXACT field names from metadata (case-sensitive)
            3. For enum fields: call get_enum_metadata() for valid values
            4. Check if entity supports dataareaid before using it
            5. DO NOT guess field names, types, or values

            FIELD RULES:
            - Field names: EXACT spelling from get_entity_metadata()
            - Field values: Correct data types (string, number, boolean, date)
            - Required fields: Include all fields marked as required in metadata
            - Enum fields: Use exact enum values from get_enum_metadata()

            DATA TYPE RULES:
            - Dates: "2024-01-01T00:00:00Z" format
            - Numbers: Use 123 not "123"
            - Booleans: Use true not "true" 
            - Enum values: Use exact syntax from enum metadata

            COMPANY RULES:
            - Check metadata: only use dataareaid if field exists in entity
            - Company field names vary: "dataareaid", "legalentityid", etc.
            - If no company field in metadata, entity is global (no dataareaid)

            Args:
                entity_name: Entity name from search_entities
                data: JSON with EXACT field names from get_entity_metadata()
                dataareaid: Only if entity has dataareaid field in metadata

            Examples:
                # WRONG - guessing field names
                create_odata_entity("Customer", {"name": "test"})
                
                # RIGHT - using metadata first  
                get_entity_metadata("CustomersV3")  # Get exact field names
                create_odata_entity("CustomersV3", {"CustomerName": "test", "CustomerGroupId": "10"})
            """
            try:
                result = await d365_client.create_odata_entity(entity_name, data, dataareaid) 
                
                return json.dumps(result, indent=2, default=str)
            except Exception as e:
                logger.error("Entity creation failed", error=str(e))
                raise FastMCPError(f"Failed to create {entity_name}: {e}")
    
    @staticmethod
    def _register_instruction_tools(mcp: FastMCP, instructions_service: IInstructionsService) -> None:
        """Register instruction management tools with comprehensive guidance"""
        
        @mcp.tool
        async def get_entity_instructions(entity_name: str, operation_type: str = "all") -> str:
            """
            Get usage instructions for a specific entity and operation.

            Returns learned patterns and examples from successful entity usage.
            Use this to understand how to effectively work with D365 entities.

            Args:
                entity_name: Target entity name (e.g., "CustomersV3", "LedgerJournalHeaders")
                operation_type: Operation filter ("read", "create", "update", "delete", "all")

            Returns:
                JSON with instruction guidance including:
                - instructions: List of saved usage patterns
                - success_rate: Overall success rate for this entity
                - common_patterns: Frequently used approaches
                - recent_examples: Latest successful examples
                - suggestions: Actionable guidance

            Examples:
                get_entity_instructions("LedgerJournalHeaders", "create")
                get_entity_instructions("CustomersV3", "read")
                get_entity_instructions("VendInvoiceJour", "all")
            """
            try:
                instructions_data = await instructions_service.get_entity_instructions(
                    entity_name, operation_type if operation_type != "all" else None
                )
                return json.dumps(instructions_data, indent=2, default=str)
            except Exception as e:
                logger.error("Get instructions failed", error=str(e))
                raise FastMCPError(f"Failed to get instructions for {entity_name}: {e}")

        @mcp.tool
        async def save_entity_instruction(
            entity_name: str, 
            operation_type: str, 
            instruction: Dict[str, Any], 
            update_mode: str = "merge"
        ) -> str:
            """
            Save or intelligently update instruction based on successful entity usage.

            This tool creates a single instruction per entity+operation combination. If an instruction
            already exists, it will be intelligently updated rather than creating duplicates.

            Args:
                entity_name: Target entity name
                operation_type: Operation type ("read", "create", "update", "delete")
                instruction: Instruction details with required fields:
                    - title: Brief description (required)
                    - description: Detailed explanation in plain language prompt form (required)
                    - example_query: Working OData query (optional)
                    - example_data: Sample data payload for creates/updates (optional)
                    - tags: List of relevant tags (optional)
                update_mode: How to handle existing instructions:
                    - "merge": Intelligently combine with existing (default)
                    - "replace": Completely replace existing instruction
                    - "append": Add as additional scenario to existing

            Returns:
                JSON confirmation with instruction ID and update details

            The instruction description should be written as effective prompts that explain:
            - General guidance for the operation
            - Specific scenarios and their requirements
            - Common patterns and best practices
            - Error handling and troubleshooting tips

            Example usage:
                After successfully creating a journal entry:

                instruction = {
                    "title": "Create General Journal Header",
                    "description": "To create a journal header for general ledger entries: 1) Always specify a valid JournalName that exists in the system (like 'GenJrn' for general journals). 2) Provide a descriptive Description field for audit purposes. 3) For monthly processes, include the period in the description. 4) The system will auto-populate DataAreaId if not specified. Common scenarios: Monthly accruals use 'GenJrn', Year-end adjustments use 'YrEnd', Daily operations use 'Daily'.",
                    "example_data": '{"JournalName": "GenJrn", "Description": "Monthly accruals for March 2024"}',
                    "tags": ["general-ledger", "journals", "monthly-process"]
                }

                save_entity_instruction("LedgerJournalHeaders", "create", instruction, "merge")
            """
            try:
                # Validate required fields
                if not isinstance(instruction, dict):
                    raise FastMCPError("Instruction must be a dictionary")

                required_fields = ["title", "description"]
                missing_fields = [field for field in required_fields if not instruction.get(field)]
                if missing_fields:
                    raise FastMCPError(f"Missing required fields: {', '.join(missing_fields)}")

                instruction_id = await instructions_service.save_or_update_instruction(
                    entity_name, operation_type, instruction, update_mode
                )

                response = {
                    "success": True,
                    "instruction_id": instruction_id,
                    "entity_name": entity_name,
                    "operation_type": operation_type,
                    "title": instruction.get("title"),
                    "update_mode": update_mode,
                    "message": f"Instruction saved/updated successfully with ID {instruction_id}",
                    "next_steps": [
                        f"Use get_entity_instructions('{entity_name}', '{operation_type}') to see the instruction",
                        "Rate instruction success with rate_instruction() after using it",
                        "Update with new scenarios using update_mode='append' when needed",
                    ],
                }

                return json.dumps(response, indent=2)
            except Exception as e:
                logger.error("Save instruction failed", error=str(e))
                raise FastMCPError(f"Failed to save instruction: {e}")

        logger.info("Instruction tools registered successfully")