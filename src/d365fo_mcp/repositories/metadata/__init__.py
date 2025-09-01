"""Metadata repository implementations"""

from .interface import IMetadataRepository

# Note: Concrete implementations should be imported from their specific packages
# to avoid circular imports. Use:
# from ..sqlite import SQLiteMetadataRepository
# from ..supabase import SupabaseMetadataRepository

__all__ = [
    "IMetadataRepository",
]