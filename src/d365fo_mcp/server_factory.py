"""
Server Factory for D365FO MCP Server

Creates fully configured server instances using dependency injection and factory patterns.
"""

import structlog
from fastmcp import FastMCP

from .config import get_settings
from .di_container import DIContainer
from .factories import AuthProviderFactory, ClientFactory, RepositoryFactory, ServiceFactory
from .tools.registry import ToolRegistry
from .tools.capabilities import create_ledger_tools

logger = structlog.get_logger(__name__)


class ServerFactory:
    """
    Factory for creating fully configured D365FO MCP server instances.
    
    Uses a centralized DI container to manage dependencies with proper
    abstraction layers and separation of concerns.
    """
    
    @staticmethod
    async def create_configured_server() -> FastMCP:
        """
        Create a fully configured and ready-to-run MCP server using dependency injection.
        
        Returns:
            FastMCP server with all services initialized and tools registered
        """
        logger.info("Creating D365FO MCP Server with dependency injection")
        
        try:
            # Create MCP server instance
            mcp = FastMCP(name="D365FO-MCP-Server", version="0.2.0")
            
            # Load settings
            settings = get_settings()
            logger.info("Configuration loaded", 
                       auth_provider=settings.auth_provider,
                       d365_client=settings.d365_client,
                       metadata_repo=settings.metadata_repository,
                       instructions_repo=settings.instructions_repository)
            
            # Create dependencies using factories (Dependency Injection)
            
            # 1. Create authentication provider
            auth_provider = AuthProviderFactory.create(settings)
            
            # Validate credentials on startup
            if not await auth_provider.validate_credentials():
                raise RuntimeError("Failed to validate D365 credentials")
            
            # 2. Create D365 client
            d365_client = await ClientFactory.create(settings, auth_provider)
            
            # 3. Create repositories
            metadata_repository = RepositoryFactory.create_metadata_repository(settings)
            instructions_repository = RepositoryFactory.create_instructions_repository(settings)
            
            # 4. Create services using factory (inject repository dependencies)
            metadata_service = ServiceFactory.create_metadata_service(metadata_repository, d365_client)
            instructions_service = ServiceFactory.create_instructions_service(instructions_repository)
            
            # 5. Initialize all services
            await metadata_service.initialize()
            await instructions_service.initialize()
            
            # 6. Optional: Start background sync if using SQLite (future enhancement)
            # TODO: Move background sync to service layer
            
            # 7. Register base tools using registry (inject service dependencies)
            ToolRegistry.register_all_tools(mcp, metadata_service, d365_client, instructions_service)
            
            # 8. Create specialized capability tools using transformations
            #await create_ledger_tools(mcp)
            
            # 9. Store service references for cleanup
            mcp._metadata_service = metadata_service
            mcp._instructions_service = instructions_service
            mcp._auth_provider = auth_provider
            
            logger.info("D365FO MCP Server created successfully with dependency injection", 
                       total_tools=len(await mcp.get_tools()))
            return mcp
            
        except Exception as e:
            logger.error("Failed to create MCP server", error=str(e))
            raise


class ServerValidator:
    """
    Utility class for server validation and setup using dependency injection.
    """
    
    @staticmethod
    async def validate_configuration() -> None:
        """Validate configuration and D365 connectivity using DI architecture"""
        print("🔧 Validating D365FO MCP Configuration...")

        try:
            # Load and validate settings
            settings = get_settings()
            print(f"✅ Configuration loaded")
            print(f"   - D365 Base URL: {settings.d365_base_url}")
            print(f"   - Default Company: {settings.dataareaid}")
            print(f"   - Database Path: {settings.database_path_resolved}")
            print(f"   - Auth Provider: {settings.auth_provider}")
            print(f"   - D365 Client: {settings.d365_client}")
            print(f"   - Repositories: {settings.metadata_repository}/{settings.instructions_repository}")

            # Test repositories
            try:
                metadata_repo = RepositoryFactory.create_metadata_repository(settings)
                instructions_repo = RepositoryFactory.create_instructions_repository(settings)
                
                await metadata_repo.initialize()
                await instructions_repo.initialize()
                
                print("✅ Repository initialization successful")
                
                await metadata_repo.close()
                await instructions_repo.close()
                
            except Exception as e:
                print(f"❌ Repository initialization failed: {e}")
                return

            # Test D365 authentication using factory
            try:
                auth_provider = AuthProviderFactory.create(settings)
                if await auth_provider.validate_credentials():
                    print("✅ D365 authentication successful")
                else:
                    print("❌ D365 authentication failed")
                    return
            except Exception as e:
                print(f"❌ Authentication provider failed: {e}")
                return

            # Test D365 client using factory
            try:
                client = await ClientFactory.create(settings, auth_provider)
                
                # Try to fetch metadata (basic connectivity test)
                metadata_xml = await client.list_odata_entities()
                print(f"✅ D365 metadata fetch successful ({len(metadata_xml):,} bytes)")
                
                client_info = client.get_client_info()
                print(f"   - Client Type: {client_info.get('type')}")
                print(f"   - Capabilities: {', '.join(client_info.get('capabilities', []))}")
                
            except Exception as e:
                print(f"❌ D365 client failed: {e}")
                return

            print("\n🎉 Configuration validation completed successfully!")
            print("   Your D365FO MCP server with dependency injection is ready to use.")

        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
    
    @staticmethod
    async def initialize_database_only() -> None:
        """Initialize database schema using repository factories"""
        print("🗄️  Initializing D365FO MCP Database using repository pattern...")

        try:
            settings = get_settings()
            
            # Initialize repositories (this will create the database schema)
            metadata_repo = RepositoryFactory.create_metadata_repository(settings)
            instructions_repo = RepositoryFactory.create_instructions_repository(settings)
            
            await metadata_repo.initialize()
            await instructions_repo.initialize()

            print(f"✅ Database initialized at: {settings.database_path_resolved}")
            print("   Repository pattern successfully applied:")
            print("   - Metadata repository initialized")
            print("   - Instructions repository initialized")
            print("   - All database tables and indexes created")
            
            # Get repository info
            metadata_info = await metadata_repo.get_repository_info()
            instructions_info = await instructions_repo.get_repository_info()
            
            print(f"   - Metadata capabilities: {', '.join(metadata_info.get('capabilities', []))}")
            print(f"   - Instructions capabilities: {', '.join(instructions_info.get('capabilities', []))}")
            
            await metadata_repo.close()
            await instructions_repo.close()

        except Exception as e:
            print(f"❌ Database initialization failed: {e}")