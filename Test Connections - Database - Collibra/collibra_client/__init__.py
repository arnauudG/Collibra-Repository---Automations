"""
Collibra API Client Library.

A clean, well-structured Python client for interacting with Collibra's REST API
using OAuth 2.0 client credentials authentication.

This package provides a high-level interface for Collibra API operations with
automatic authentication handling, token management, and comprehensive error handling.

Main Components:
    - CollibraClient: Main API client for making authenticated requests
    - CollibraAuthenticator: OAuth 2.0 authentication handler
    - CollibraConfig: Configuration management with environment variable support
    - Custom exceptions for detailed error handling

Quick Start:
    >>> from collibra_client import CollibraClient, CollibraConfig
    >>>
    >>> # Load configuration from environment variables
    >>> config = CollibraConfig.from_env()
    >>>
    >>> # Create client
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

For more information, see the README.md file or visit the project repository.
"""

# Core functionality
from collibra_client.core import (
    CollibraClient,
    CollibraAuthenticator,
    CollibraConfig,
    CollibraAuthenticationError,
    CollibraAPIError,
    CollibraClientError,
)

# Catalog/Database functionality
from collibra_client.catalog import (
    DatabaseConnection,
    DatabaseConnectionManager,
)

# Notifications functionality
from collibra_client.notifications import (
    NotificationHandler,
    CollibraNotificationHandler,
    ConsoleNotificationHandler,
    EmailNotificationHandler,
    get_connection_owner,
)

__all__ = [
    "CollibraClient",
    "CollibraAuthenticator",
    "CollibraConfig",
    "DatabaseConnection",
    "DatabaseConnectionManager",
    "NotificationHandler",
    "CollibraNotificationHandler",
    "ConsoleNotificationHandler",
    "EmailNotificationHandler",
    "get_connection_owner",
    "CollibraAuthenticationError",
    "CollibraAPIError",
    "CollibraClientError",
]

__version__ = "1.0.0"

