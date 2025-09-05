#!/usr/bin/env python3
"""
Manual D365 Metadata Sync Script

This script manually triggers a metadata sync from your D365 environment
to populate the local SQLite database with entity definitions, properties,
and enum values.

Usage:
    python scripts/manual_sync.py

Requirements:
    - Valid .env file with D365 credentials
    - Network access to your D365 environment
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from dotenv import load_dotenv
load_dotenv()

async def main():
    """Run manual metadata synchronization"""
    try:
        from d365fo_mcp.auth.d365_auth import D365AuthManager
        from d365fo_mcp.config import get_settings
        from d365fo_mcp.factories.client_factory import ClientFactory
        from d365fo_mcp.repositories.sqlite.database import Database
        from d365fo_mcp.services.metadata.background_sync import BackgroundMetadataSync
        
        print('🚀 Starting manual D365 metadata sync...')
        print('   This will download and process metadata from your D365 environment')
        
        # Load settings and show what we're connecting to
        settings = get_settings()
        print(f'   Connecting to: {settings.d365_resource_url}')
        print(f'   Database: {settings.database_path_resolved}')
        
        # Create authentication and D365 client
        print('\n🔐 Authenticating with D365...')
        auth = D365AuthManager()
        d365_client = await ClientFactory.create(settings, auth)
        print('✅ Authentication successful')
        
        # Initialize database
        print('\n💾 Initializing database...')
        database = Database(settings.database_path_resolved)
        await database.initialize()
        print('✅ Database ready')
        
        # Create sync service and run sync
        print('\n📡 Starting metadata download and processing...')
        sync_service = BackgroundMetadataSync(database, d365_client)
        
        start_time = time.time()
        result = await sync_service.force_sync_now()
        duration = time.time() - start_time
        
        print(f'\n✅ Sync completed in {duration:.1f} seconds!')
        print('\n📊 Results:')
        print(f'   Entity types processed: {result.get("entity_types_parsed", 0):,}')
        print(f'   Entity properties: {result.get("properties_parsed", 0):,}')
        print(f'   Navigation properties: {result.get("navigation_props_parsed", 0):,}')
        print(f'   Enum types: {result.get("enum_types_parsed", 0):,}')
        print(f'   Enum members: {result.get("enum_members_parsed", 0):,}')
        print(f'   Metadata size: {result.get("xml_size_bytes", 0):,} bytes')
        print(f'   Processing rate: {result.get("records_per_second", 0):,.0f} records/sec')
        
        # Show some sample entities
        conn = await database.get_connection()
        cursor = conn.execute('SELECT name FROM entity_sets LIMIT 10')
        samples = [row[0] for row in cursor.fetchall()]
        
        print(f'\n🔍 Sample entities now available for search:')
        for i, entity in enumerate(samples, 1):
            print(f'   {i:2d}. {entity}')
        
        await database.close()
        print(f'\n🎯 Database populated successfully!')
        print(f'   Your D365FO MCP server can now search and query these entities.')
        
    except KeyboardInterrupt:
        print('\n⚠️  Sync cancelled by user')
        sys.exit(1)
    except Exception as e:
        print(f'\n❌ Sync failed: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())