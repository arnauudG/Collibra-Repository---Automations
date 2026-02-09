"""
Catalog Database Registration API functionality.

This module provides functionality to manage and test database connections
in Collibra's Catalog Database Registration API.
"""

from collibra_client.catalog.connections import (
    DatabaseConnection,
    DatabaseConnectionManager,
)

__all__ = [
    "DatabaseConnection",
    "DatabaseConnectionManager",
]

