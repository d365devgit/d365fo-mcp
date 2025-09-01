"""
MCP Tools for D365FO MCP Server

Registry and capability-based tools using proper dependency injection patterns.
"""

from .registry import ToolRegistry
from .capabilities import create_ledger_tools

__all__ = ["ToolRegistry", "create_ledger_tools"]
