"""
D365 Authentication Manager

Azure AD implementation of IAuthProvider for D365 Finance & Operations.
"""

import time
from typing import Dict, Any, Optional
from azure.identity import DefaultAzureCredential, ClientSecretCredential
import structlog

from ..config import get_settings
from .interface import IAuthProvider, AuthenticationError

logger = structlog.get_logger(__name__)


class D365AuthManager(IAuthProvider):
    """Manages Azure AD authentication for D365 Finance & Operations"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.token_cache: Dict[str, Dict[str, Any]] = {}

        # Use client secret credential for service principal authentication
        self.credential = ClientSecretCredential(
            tenant_id=self.settings.azure_tenant_id,
            client_id=self.settings.azure_client_id,
            client_secret=self.settings.azure_client_secret,
        )

        logger.info(
            "D365 Auth Manager initialized",
            tenant_id=self.settings.azure_tenant_id,
            client_id=self.settings.azure_client_id,
            d365_base_url=self.settings.d365_base_url,
        )

    async def get_d365_token(self, user_context: Dict[str, str]) -> str:
        """
        Get D365 access token using client credentials flow

        Args:
            user_context: User context (for compatibility, not used in client credentials)

        Returns:
            Valid access token for D365 Finance & Operations
        """
        cache_key = f"d365_{user_context.get('user_id', 'system')}"

        # Check cache first
        if cache_key in self.token_cache:
            token_data = self.token_cache[cache_key]
            if token_data["expires_at"] > time.time() + 60:  # 60 second buffer
                logger.debug("Using cached D365 token", cache_key=cache_key)
                return str(token_data["token"])

        try:
            # Get token for D365 Finance & Operations
            scope = f"{self.settings.d365_resource_url}/.default"

            logger.debug("Requesting new D365 token", scope=scope)
            token = self.credential.get_token(scope)

            # Cache the token
            self.token_cache[cache_key] = {"token": token.token, "expires_at": token.expires_on}

            logger.info(
                "D365 token acquired successfully", cache_key=cache_key, expires_at=token.expires_on
            )

            return str(token.token)

        except Exception as e:
            logger.error(
                "Failed to acquire D365 token",
                error=str(e),
                tenant_id=self.settings.azure_tenant_id,
                client_id=self.settings.azure_client_id,
            )
            raise AuthenticationError(f"Failed to acquire D365 token: {e}") from e

    def clear_token_cache(self) -> None:
        """Clear the token cache (useful for testing or token refresh issues)"""
        self.token_cache.clear()
        logger.info("Token cache cleared")

    async def validate_credentials(self) -> bool:
        """
        Validate that the credentials can successfully authenticate with D365

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            token = await self.get_d365_token({"user_id": "validation_test"})
            return bool(token)
        except Exception as e:
            logger.error("Credential validation failed", error=str(e))
            return False
    
    # Interface methods with different signatures - map to existing implementation
    async def get_token(self, context: Dict[str, Any]) -> str:
        """Get authentication token (IAuthProvider interface method)"""
        return await self.get_d365_token(context)
    
    async def refresh_token_if_needed(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Refresh token if needed (IAuthProvider interface method)
        
        For now, we always get a fresh token since Azure handles caching internally
        """
        try:
            return await self.get_d365_token(context)
        except Exception:
            return None
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information (IAuthProvider interface method)"""
        return {
            "type": "azure_ad",
            "tenant_id": self.settings.azure_tenant_id,
            "client_id": self.settings.azure_client_id,
            "cache_size": len(self.token_cache),
            "resource_url": self.settings.d365_resource_url
        }
