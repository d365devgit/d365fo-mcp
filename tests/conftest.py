"""
Pytest configuration and fixtures for D365FO MCP tests
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from d365fo_mcp.repositories.sqlite import Database
from d365fo_mcp.config import Settings


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_database():
    """Create a temporary test database"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)

    database = Database(db_path)
    await database.initialize()

    yield database

    await database.close()
    db_path.unlink()


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    return Settings(
        azure_client_id="test-client-id",
        azure_client_secret="test-client-secret",
        azure_tenant_id="test-tenant-id",
        d365_instance="test-instance",
        dataareaid="test",
        database_path=":memory:",
    )


@pytest.fixture
def mock_d365_client():
    """Mock D365Client for testing"""
    client = AsyncMock()
    client.get_odata_entity.return_value = {
        "value": [{"Name": "Test", "Id": "123"}],
        "@odata.count": 1,
    }
    client.create_odata_entity.return_value = {"Id": "123", "Name": "Test"}
    client.list_odata_entities.return_value = "<xml>mock metadata</xml>"
    return client


@pytest.fixture
def mock_auth_manager():
    """Mock D365AuthManager for testing"""
    auth = AsyncMock()
    auth.get_d365_token.return_value = "mock-token"
    auth.validate_credentials.return_value = True
    return auth


@pytest.fixture
def sample_instruction():
    """Sample instruction for testing"""
    return {
        "title": "Create Test Record",
        "description": "Example of creating a test record",
        "example_query": "?$filter=Name eq 'Test'",
        "example_data": '{"Name": "Test", "Value": "123"}',
        "tags": ["test", "example"],
    }
