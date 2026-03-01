"""
Collibra API Client Library.

A clean, well-structured Python client for interacting with Collibra's REST API
with support for both OAuth 2.0 and Basic Authentication.

This package provides a high-level interface for Collibra API operations with
automatic authentication handling, token management, and comprehensive error handling.

Main Components:
    - CollibraClient: Main API client for making authenticated requests
    - CollibraAuthenticator: OAuth 2.0 authentication handler
    - BasicAuthenticator: Basic Authentication handler (username/password)
    - CollibraConfig: Configuration management with environment variable support
    - Custom exceptions for detailed error handling

Quick Start (OAuth 2.0):
    >>> from collibra_client import CollibraClient, CollibraConfig
    >>>
    >>> # Load configuration from environment variables
    >>> config = CollibraConfig.from_env()
    >>>
    >>> # Create client with OAuth
    >>> client = CollibraClient(
    ...     base_url=config.base_url,
    ...     client_id=config.client_id,
    ...     client_secret=config.client_secret
    ... )
    >>>
    >>> # Test connection
    >>> client.test_connection()
    >>>
    >>> # Make API calls
    >>> users = client.get("/rest/2.0/users")

Quick Start (Basic Auth):
    >>> # Create client with username/password
    >>> client = CollibraClient(
    ...     base_url="https://instance.collibra.com",
    ...     username="your_username",
    ...     password="your_password"
    ... )
    >>>
    >>> # Test connection
    >>> client.test_connection()

For more information, see the README.md file or visit the project repository.
"""

# Core functionality
# Catalog/Database functionality
from collibra_client.catalog import (
    DatabaseConnection,
    DatabaseConnectionManager,
)
from collibra_client.core import (
    BasicAuthenticator,
    CollibraAPIError,
    CollibraAuthenticationError,
    CollibraAuthenticator,
    CollibraClient,
    CollibraClientError,
    CollibraConfig,
)

__all__ = [
    "CollibraClient",
    "CollibraAuthenticator",
    "BasicAuthenticator",
    "CollibraConfig",
    "DatabaseConnection",
    "DatabaseConnectionManager",
    "CollibraAuthenticationError",
    "CollibraAPIError",
    "CollibraClientError",
]

__version__ = "1.0.0"
