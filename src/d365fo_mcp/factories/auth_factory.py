"""
Authentication Provider Factory

Creates auth provider instances based on configuration.
"""

from typing import Dict, Any
import structlog

from ..config import Settings
from ..auth import IAuthProvider, D365AuthManager

logger = structlog.get_logger(__name__)


class MockAuthProvider(IAuthProvider):
    """Mock auth provider for testing"""
    
    def __init__(self):
        self.mock_token = "mock_bearer_token_12345"
    
    async def validate_credentials(self) -> bool:
        """Always returns True for mock"""
        return True
    
    async def get_token(self, context: Dict[str, Any]) -> str:
        """Returns mock token"""
        return self.mock_token
    
    async def refresh_token_if_needed(self, context: Dict[str, Any]) -> str | None:
        """Returns same mock token"""
        return self.mock_token
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Returns mock provider info"""
        return {
            "type": "mock",
            "mock_token": self.mock_token[:20] + "...",
            "status": "active"
        }


class AuthProviderFactory:
    """Factory for creating authentication providers"""
    
    @staticmethod
    def create(settings: Settings) -> IAuthProvider:
        """
        Create auth provider based on configuration.
        
        Args:
            settings: Application settings
            
        Returns:
            Configured auth provider instance
            
        Raises:
            ValueError: If provider type is not supported
        """
        provider_type = settings.auth_provider.lower()
        
        logger.info("Creating auth provider", provider_type=provider_type)
        
        if provider_type == "azure_ad":
            return D365AuthManager()
        elif provider_type == "mock":
            return MockAuthProvider()
        else:
            raise ValueError(f"Unsupported auth provider: {provider_type}")
    
    @staticmethod
    def get_available_providers() -> list[str]:
        """Get list of available auth provider types"""
        return ["azure_ad", "mock"]