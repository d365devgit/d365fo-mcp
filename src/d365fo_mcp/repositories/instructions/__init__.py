"""Instructions repository implementations"""

from .interface import IInstructionsRepository

# Note: Concrete implementations should be imported from their specific packages
# to avoid circular imports. Use:
# from ..sqlite import SQLiteInstructionsRepository
# from ..supabase import SupabaseInstructionsRepository

__all__ = [
    "IInstructionsRepository",
]