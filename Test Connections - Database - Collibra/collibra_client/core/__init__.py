"""
Core functionality for Collibra API client.

This module contains the core components:
- Authentication (OAuth 2.0)
- HTTP client
- Configuration management
- Exception definitions
"""

from collibra_client.core.auth import CollibraAuthenticator
from collibra_client.core.client import CollibraClient
from collibra_client.core.config import CollibraConfig
from collibra_client.core.exceptions import (
    CollibraAuthenticationError,
    CollibraAPIError,
    CollibraClientError,
    CollibraTokenError,
)

__all__ = [
    "CollibraClient",
    "CollibraAuthenticator",
    "CollibraConfig",
    "CollibraAuthenticationError",
    "CollibraAPIError",
    "CollibraClientError",
    "CollibraTokenError",
]

