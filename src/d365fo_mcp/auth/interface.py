"""
Authentication Provider Interface

Defines contract for authentication providers (Azure AD, Service Principal, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class IAuthProvider(ABC):
    """Interface for authentication providers"""
    
    @abstractmethod
    async def validate_credentials(self) -> bool:
        """
        Validate that credentials are properly configured and working.
        
        Returns:
            True if credentials are valid and can authenticate
        """
        pass
    
    @abstractmethod
    async def get_token(self, context: Dict[str, Any]) -> str:
        """
        Get authentication token for D365 operations.
        
        Args:
            context: Authentication context (user_id, scopes, etc.)
            
        Returns:
            Bearer token for D365 API access
            
        Raises:
            AuthenticationError: If authentication fails
        """
        pass
    
    @abstractmethod
    async def refresh_token_if_needed(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Refresh token if it's expired or about to expire.
        
        Args:
            context: Authentication context
            
        Returns:
            New token if refreshed, None if current token is still valid
        """
        pass
    
    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about the auth provider.
        
        Returns:
            Provider metadata (type, settings, etc.)
        """
        pass


class AuthenticationError(Exception):
    """Authentication related errors"""
    pass