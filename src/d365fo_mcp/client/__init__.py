"""
D365 Client module

HTTP client for interacting with D365 Finance & Operations OData APIs.
"""

from .interface import ID365Client, CompanyMode
from .d365_client import D365Client

__all__ = [
    "ID365Client", 
    "CompanyMode", 
    "D365Client"
]
