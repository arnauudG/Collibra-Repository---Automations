"""
Core functionality for Collibra API client.

This module contains the core components:
- Authentication (OAuth 2.0 and Basic Auth)
- HTTP client
- Configuration management
- Exception definitions
"""

from collibra_client.core.auth import BasicAuthenticator, CollibraAuthenticator
from collibra_client.core.client import CollibraClient
from collibra_client.core.config import CollibraConfig
from collibra_client.core.exceptions import (
    CollibraAPIError,
    CollibraAuthenticationError,
    CollibraClientError,
    CollibraTokenError,
)

__all__ = [
    "CollibraClient",
    "CollibraAuthenticator",
    "BasicAuthenticator",
    "CollibraConfig",
    "CollibraAuthenticationError",
    "CollibraAPIError",
    "CollibraClientError",
    "CollibraTokenError",
]
