"""
Ledger Capability Tools using FastMCP Tool Transformations

Creates specialized ledger tools by transforming base registry tools using FastMCP 2.0 patterns.
"""

from fastmcp import FastMCP
from fastmcp.tools import Tool
from fastmcp.tools.tool_transform import ArgTransform

import structlog
logger = structlog.get_logger(__name__)


async def create_ledger_tools(mcp: FastMCP) -> None:
    """
    Create specialized ledger tools by transforming base registry tools.
    
    This function must be called AFTER the registry tools are registered.
    """
    logger.info("Creating ledger capability tools using FastMCP transformations")
    
    # Get reference to base tools for transformation
    base_get_odata_entity = await mcp.get_tool("get_odata_entity")
    base_create_odata_entity = await mcp.get_tool("create_odata_entity")
    
    # Create specialized account finder
    find_accounts = Tool.from_tool(
        base_get_odata_entity,
        transform_args={
            "entity_name": ArgTransform(
                hide=True,
                default="MainAccounts"
            ),
            "filter_query": ArgTransform(
                name="search_criteria",
                description="Account search criteria. Examples: 'contains(MainAccount,\"1101\")', 'AccountType eq \"Asset\"', 'contains(Name,\"Cash\")'",
                required=True
            ),
            "select_fields": ArgTransform(
                default="MainAccount,Name,Description,AccountType,IsActive,IsSuspended",
                description="Fields to return (default includes standard account fields)"
            ),
            "top": ArgTransform(
                name="limit", 
                description="Maximum accounts to return",
                default=20
            ),
            "dataareaid": ArgTransform(
                name="company",
                description="Company code filter (e.g., 'USMF')"
            ),
            "orderby": ArgTransform(
                default="MainAccount asc",
                description="Sort order for results" 
            ),
            "count": ArgTransform(
                default=True,
                hide=True  # Always include count for ledger queries
            )
        },
        name="find_accounts",
        title="Find Chart of Accounts",
        description="""
Find main accounts by search criteria with ledger-specific filtering.

Key Fields:
- MainAccount: Account number (use in journal lines)
- Name: Account description  
- AccountType: Asset, Liability, Revenue, Expense, Equity
- IsActive: Whether account is active
- IsSuspended: Whether account is suspended

Usage: Find accounts for journal entry creation or validation
Examples: 
- search_criteria="contains(Name,'Cash')"
- search_criteria="AccountType eq 'Asset' and IsActive eq true"
        """.strip()
    )
    
    mcp.add_tool(find_accounts)
    
    # Create specialized dimension finder
    find_dimensions = Tool.from_tool(
        base_get_odata_entity,
        transform_args={
            "entity_name": ArgTransform(
                hide=True,
                default="DimensionAttributeValues"
            ),
            "filter_query": ArgTransform(
                name="dimension_criteria", 
                description="Dimension search criteria. Examples: 'DimensionName eq \"Department\"', 'contains(DimensionValue,\"SALES\")'",
                required=True
            ),
            "select_fields": ArgTransform(
                default="DimensionName,DimensionValue,Description,IsActive,IsSuspended",
                description="Fields to return (default includes standard dimension fields)"
            ),
            "top": ArgTransform(
                name="limit",
                description="Maximum dimension values to return",
                default=50
            ),
            "orderby": ArgTransform(
                default="DimensionName asc, DimensionValue asc",
                description="Sort order for results"
            ),
            "count": ArgTransform(
                default=True,
                hide=True
            )
        },
        name="find_dimensions",
        title="Find Financial Dimensions",
        description="""
Find financial dimension values by dimension name or search criteria.

Key Fields:
- DimensionName: Name of the dimension (Department, CostCenter, etc.)
- DimensionValue: The dimension value code
- Description: Human-readable description
- IsActive: Whether dimension value is active

Usage: Find dimension values for account string construction
Examples:
- dimension_criteria="DimensionName eq 'Department'"
- dimension_criteria="contains(DimensionValue,'SALES')"
        """.strip()
    )
    
    mcp.add_tool(find_dimensions)
    
    # Create specialized journal header creator
    create_journal_header = Tool.from_tool(
        base_create_odata_entity,
        transform_args={
            "entity_name": ArgTransform(
                hide=True,
                default="LedgerJournalHeaders"
            ),
            "data": ArgTransform(
                name="journal_data",
                description="Journal header data. Required: JournalName. Recommended: Description. Example: {'JournalName': 'GenJrn', 'Description': 'Monthly accruals'}"
            ),
            "dataareaid": ArgTransform(
                name="company",
                description="Company code for the journal"
            )
        },
        name="create_journal_header",
        title="Create General Ledger Journal Header",
        description="""
Create a new general ledger journal header for journal entries.

Required Fields:
- JournalName: Journal name template (e.g., 'GenJrn', 'APInvoice')

Recommended Fields:
- Description: Journal description for audit trail

Usage: Create journal header before adding journal lines
Example: journal_data={'JournalName': 'GenJrn', 'Description': 'Month-end accruals'}
        """.strip()
    )
    
    mcp.add_tool(create_journal_header)
    
    # Create specialized journal line creator
    create_journal_line = Tool.from_tool(
        base_create_odata_entity,
        transform_args={
            "entity_name": ArgTransform(
                hide=True,
                default="LedgerJournalLines"
            ),
            "data": ArgTransform(
                name="line_data",
                description="Journal line data. Required: JournalNum, AccountString, DebitAmount or CreditAmount. Example: {'JournalNum': 'GL_123456', 'AccountString': '110110-001-022', 'DebitAmount': 1000.00, 'Description': 'Accrued revenue'}"
            ),
            "dataareaid": ArgTransform(
                name="company",
                description="Company code for the journal line"
            )
        },
        name="create_journal_line",
        title="Create General Ledger Journal Line",
        description="""
Create a journal line entry within an existing journal header.

Required Fields:
- JournalNum: Journal number from created header
- AccountString: Full account string (e.g., '110110-001-022')
- DebitAmount OR CreditAmount: Transaction amount

Optional Fields:
- Description: Line description
- CurrencyCode: Currency (defaults to company currency)

Usage: Add individual accounting entries to journal
Example: line_data={'JournalNum': 'GL_123456', 'AccountString': '110110-001-022', 'DebitAmount': 1000.00}
        """.strip()
    )
    
    mcp.add_tool(create_journal_line)
    
    logger.info("Ledger capability tools created successfully")