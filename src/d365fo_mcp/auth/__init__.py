"""
Authentication module for D365FO MCP Server

Handles Azure AD authentication for D365 Finance & Operations access.
"""

from .interface import IAuthProvider, AuthenticationError
from .d365_auth import D365AuthManager

__all__ = [
    "IAuthProvider", 
    "AuthenticationError",
    "D365AuthManager"
]
