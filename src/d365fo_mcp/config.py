"""
Configuration management for D365FO MCP Server
"""

import os
from pathlib import Path
from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # D365 Authentication (Required)
    azure_client_id: str
    azure_client_secret: str
    azure_tenant_id: str
    d365_instance: str

    # Optional Configuration
    dataareaid: str = "usmf"
    database_path: str = os.getenv('DATABASE_PATH', str(Path(__file__).parent.parent.parent / 'data' / 'd365fo-mcp.db'))
    metadata_cache_hours: int = 24
    log_level: str = "info"

    # Development Settings
    debug: bool = False
    sqlite_echo: bool = False
    
    # Implementation Selection (for Dependency Injection)
    auth_provider: Literal["azure_ad", "mock"] = "azure_ad"
    d365_client: Literal["odata", "mock"] = "odata"
    metadata_repository: Literal["sqlite", "supabase"] = "sqlite"
    instructions_repository: Literal["sqlite", "supabase"] = "sqlite"
    
    # Supabase Configuration (for future use)
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    @property
    def database_path_resolved(self) -> Path:
        """Get resolved database path"""
        return Path(self.database_path).resolve()

    @property
    def d365_resource_url(self) -> str:
        """Get D365 resource URL"""
        return f"https://{self.d365_instance}.operations.dynamics.com"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton"""
    global _settings
    if _settings is None:
        # Ensure .env is loaded before creating settings
        load_dotenv_if_exists()
        
        # Debug environment variables
        import structlog
        logger = structlog.get_logger(__name__)
        logger.info("Environment variables", 
                   database_path=os.getenv('DATABASE_PATH'),
                   d365_instance=os.getenv('D365_INSTANCE'),
                   cwd=os.getcwd())
        
        try:
            _settings = Settings()  # type: ignore[call-arg]
            logger.info("Settings loaded", database_path=_settings.database_path)
        except Exception:
            # Re-raise with more context
            raise ValueError("Required environment variables missing. Check your .env file.")
    return _settings


def load_dotenv_if_exists() -> None:
    """Load .env file if it exists"""
    from dotenv import load_dotenv

    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try to load from parent directories
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            env_path = parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                break
