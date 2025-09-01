"""
D365 Finance & Operations OData Client

Extracted and simplified from FinOpsAgent for the d365fo-mcp server.
Handles OData operations with proper company context management.
"""

import re
from typing import Optional, Literal, Dict, Any
import httpx
import structlog

from ..config import get_settings
from ..auth import IAuthProvider
from .interface import ID365Client, CompanyMode

logger = structlog.get_logger(__name__)


class D365Client(ID365Client):
    """HTTP client for D365 Finance & Operations OData APIs with automatic token refresh"""

    def __init__(self, token: str, auth_provider: Optional[IAuthProvider] = None):
        self.token = token
        self.auth_provider = auth_provider
        self.settings = get_settings()
        self.resource = self.settings.d365_resource_url
        self._user_default_company: Optional[str] = None

    async def get_user_default_company(self) -> str:
        """
        Get the user's default company from configuration.
        Caches the result to avoid repeated lookups.
        """
        if self._user_default_company is not None:
            return self._user_default_company

        # Use configured default company
        default_company = self.settings.dataareaid.lower()
        self._user_default_company = default_company

        logger.info("User default company set", company=default_company)
        return default_company

    async def refresh_token_if_needed(self) -> bool:
        """
        Refresh the access token using the auth provider.
        
        Returns:
            True if token was refreshed, False if no auth provider available
        """
        if not self.auth_provider:
            logger.warning("No auth provider available for token refresh")
            return False
            
        try:
            new_token = await self.auth_provider.refresh_token_if_needed({"user_id": "system"})
            if new_token:
                self.token = new_token
                logger.info("Token refreshed successfully")
                return True
            return False
        except Exception as e:
            logger.error("Failed to refresh token", error=str(e))
            return False

    async def make_authenticated_request(
        self, method: str, url: str, **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request with automatic token refresh on 401 errors.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for httpx request
            
        Returns:
            HTTP response
            
        Raises:
            httpx.HTTPStatusError: If request fails after token refresh attempt
        """
        # Extract timeout for client creation
        timeout = kwargs.pop('timeout', 30.0)
        
        # Ensure headers are set
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Authorization'] = f"Bearer {self.token}"
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(method, url, **kwargs)
                    response.raise_for_status()
                    return response
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401 and attempt < max_retries - 1:
                    logger.warning("Received 401 Unauthorized, attempting token refresh", 
                                 attempt=attempt + 1, max_retries=max_retries)
                    
                    # Try to refresh token
                    if await self.refresh_token_if_needed():
                        # Update authorization header with new token
                        kwargs['headers']['Authorization'] = f"Bearer {self.token}"
                        logger.info("Retrying request with refreshed token")
                        continue
                    else:
                        logger.error("Token refresh failed, cannot retry request")
                        
                # Either not 401, max retries reached, or token refresh failed
                logger.error("HTTP request failed", 
                           method=method, url=url, status_code=e.response.status_code,
                           response_text=e.response.text)
                raise
                
            except Exception as e:
                logger.error("Request error", method=method, url=url, error=str(e))
                raise

    def determine_company_mode(self, query: str, user_default_company: str) -> CompanyMode:
        """
        Determine the company query mode based on the query parameters.

        Args:
            query: The OData query string
            user_default_company: The user's default company

        Returns:
            CompanyMode indicating how to handle company parameters
        """
        # Check if dataAreaId filter is present in the query
        dataareaid_match = re.search(r"dataAreaId\s+eq\s+'([^']+)'", query, re.IGNORECASE)

        if not dataareaid_match:
            # No dataAreaId filter = query all companies
            return "all"

        target_company = dataareaid_match.group(1).lower()

        if target_company == user_default_company.lower():
            return "default"
        else:
            return "specific"

    def build_query_url(
        self, entity_name: str, query: str, user_default_company: str, company_mode: CompanyMode
    ) -> str:
        """
        Build the proper OData query URL based on D365 company behavior rules.

        Microsoft's documented D365 OData behavior:
        - Default company: No cross-company parameter, no dataAreaId filter
        - Specific non-default company: Both cross-company=true AND dataAreaId filter
        - All companies: Only cross-company=true (no dataAreaId filter)
        """
        base_url = f"{self.resource}/data/{entity_name}"

        # Ensure query starts with '?' if it has content
        if query and not query.startswith("?"):
            query = f"?{query}"
        elif not query:
            query = ""

        if company_mode == "default":
            # Default company: No cross-company, remove any existing dataAreaId filter
            clean_query = re.sub(
                r"[&?]?dataAreaId\s+eq\s+'[^']+'\s*[&]?", "", query, flags=re.IGNORECASE
            )
            clean_query = re.sub(r"[&]{2,}", "&", clean_query)
            clean_query = re.sub(r"[?]&", "?", clean_query)
            clean_query = clean_query.rstrip("&")
            return f"{base_url}{clean_query}"

        elif company_mode == "specific":
            # Specific non-default company: Both cross-company=true AND dataAreaId filter
            if "cross-company" not in query:
                separator = "&" if "?" in query else "?"
                query += f"{separator}cross-company=true"
            return f"{base_url}{query}"

        elif company_mode == "all":
            # All companies: Only cross-company=true, remove any dataAreaId filter
            clean_query = re.sub(
                r"[&?]?dataAreaId\s+eq\s+'[^']+'\s*[&]?", "", query, flags=re.IGNORECASE
            )
            clean_query = re.sub(r"[&]{2,}", "&", clean_query)
            clean_query = re.sub(r"[?]&", "?", clean_query)
            clean_query = clean_query.rstrip("&")

            # Ensure cross-company parameter is added
            if "cross-company" not in clean_query:
                separator = "&" if "?" in clean_query else "?"
                clean_query += f"{separator}cross-company=true"
            return f"{base_url}{clean_query}"

        else:
            raise ValueError(f"Unknown company mode: {company_mode}")

    def get_headers(self) -> Dict[str, str]:
        """Get standard HTTP headers for D365 OData requests"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }

    async def get_odata_entity(
        self, entity_name: str, query: str = "", company_mode: str = "auto"
    ) -> Dict[str, Any]:
        """
        Query any D365 OData entity with proper company context management.

        Args:
            entity_name: The OData entity set name
            query: OData query parameters
            company_mode: Company query mode ("auto", "default", "specific", "all")

        Returns:
            JSON response from D365 OData API
        """
        user_default_company = await self.get_user_default_company()

        # Determine company mode automatically if requested
        if company_mode == "auto":
            resolved_company_mode = self.determine_company_mode(query, user_default_company)
        else:
            resolved_company_mode = company_mode  # type: ignore

        # Build the query URL
        url = self.build_query_url(entity_name, query, user_default_company, resolved_company_mode)

        logger.info(
            "Querying D365 entity",
            entity_name=entity_name,
            company_mode=resolved_company_mode,
            url=url,
        )

        try:
            response = await self.make_authenticated_request("GET", url)
            result: Dict[str, Any] = response.json()

            logger.info(
                "D365 query successful",
                entity_name=entity_name,
                record_count=len(result.get("value", [])),
            )

            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                "D365 query failed",
                entity_name=entity_name,
                status_code=e.response.status_code,
                response_text=e.response.text,
            )
            raise
        except Exception as e:
            logger.error("D365 query error", entity_name=entity_name, error=str(e))
            raise

    async def create_odata_entity(
        self, entity_name: str, data: Dict[str, Any], company: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new record in any D365 OData entity.

        Args:
            entity_name: The OData entity set name
            data: Record data to create
            company: Company/legal entity ID (uses default if not specified)

        Returns:
            Created record from D365 OData API
        """
        url = f"{self.resource}/data/{entity_name}"

        # Add company context if provided
        if company:
            data["dataAreaId"] = company
        elif not data.get("dataAreaId"):
            data["dataAreaId"] = self.settings.dataareaid

        logger.info(
            "Creating D365 entity record", entity_name=entity_name, company=data.get("dataAreaId")
        )

        try:
            response = await self.make_authenticated_request("POST", url, json=data)
            result: Dict[str, Any] = response.json()

            logger.info(
                "D365 create successful",
                entity_name=entity_name,
                record_id=result.get("RecId") or result.get("id"),
            )

            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                "D365 create failed",
                entity_name=entity_name,
                status_code=e.response.status_code,
                response_text=e.response.text,
            )
            raise
        except Exception as e:
            logger.error("D365 create error", entity_name=entity_name, error=str(e))
            raise

    async def list_odata_entities(self) -> str:
        """
        Get D365 OData metadata XML.

        Returns:
            Raw XML metadata from D365 OData service
        """
        url = f"{self.resource}/data/$metadata"

        logger.info("Fetching D365 metadata")

        try:
            response = await self.make_authenticated_request(
                "GET", url, 
                headers={"Accept": "application/xml"},
                timeout=60.0
            )
            metadata_xml = response.text

            logger.info("D365 metadata retrieved", size_bytes=len(metadata_xml))

            return metadata_xml

        except httpx.HTTPStatusError as e:
            logger.error(
                "D365 metadata fetch failed",
                status_code=e.response.status_code,
                response_text=e.response.text,
            )
            raise
        except Exception as e:
            logger.error("D365 metadata fetch error", error=str(e))
            raise
    
    # Missing interface methods
    async def update_odata_entity(
        self,
        entity_name: str,
        key_values: Dict[str, Any],
        data: Dict[str, Any],
        dataareaid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update existing entity record via OData PATCH.
        
        Args:
            entity_name: Target entity name
            key_values: Key field values to identify record
            data: Fields to update
            dataareaid: Company code
            
        Returns:
            Updated record data
        """
        # TODO: Implement OData PATCH operation
        # For now, raise NotImplementedError as this wasn't in the original implementation
        raise NotImplementedError("Update operations not yet implemented")
    
    async def delete_odata_entity(
        self,
        entity_name: str,
        key_values: Dict[str, Any],
        dataareaid: Optional[str] = None,
    ) -> bool:
        """
        Delete entity record via OData DELETE.
        
        Args:
            entity_name: Target entity name
            key_values: Key field values to identify record
            dataareaid: Company code
            
        Returns:
            True if deletion successful
        """
        # TODO: Implement OData DELETE operation
        # For now, raise NotImplementedError as this wasn't in the original implementation
        raise NotImplementedError("Delete operations not yet implemented")
    
    def get_client_info(self) -> Dict[str, Any]:
        """
        Get client implementation information.
        
        Returns:
            Client metadata (type, version, capabilities, etc.)
        """
        return {
            "type": "odata_client",
            "version": "1.0.0",
            "resource_url": self.resource,
            "default_company": self.settings.dataareaid,
            "capabilities": ["get", "create", "list_metadata"],
            "planned_capabilities": ["update", "delete"]
        }
