"""
Configuration management for Collibra client.

This module provides utilities for loading configuration from
environment variables or other sources.
"""

import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class CollibraConfig:
    """
    Configuration class for Collibra client settings.

    This class manages configuration for the Collibra client, supporting
    both direct parameter initialization and environment variable loading.
    It validates that all required configuration values are present.

    Configuration can be provided in two ways:
    1. Direct initialization with parameters
    2. Loading from environment variables (with optional parameter overrides)

    Attributes:
        base_url: Base URL of the Collibra instance.
        client_id: OAuth client ID for authentication.
        client_secret: OAuth client secret for authentication.
        basic_auth_username: Optional username for Basic Authentication (for Catalog API).
        basic_auth_password: Optional password for Basic Authentication (for Catalog API).
        timeout: Request timeout in seconds (default: 30).

    Examples:
        >>> # From environment variables
        >>> config = CollibraConfig.from_env()
        >>>
        >>> # Direct initialization
        >>> config = CollibraConfig(
        ...     base_url="https://instance.collibra.com",
        ...     client_id="client_id",
        ...     client_secret="client_secret",
        ...     timeout=60
        ... )
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        basic_auth_username: Optional[str] = None,
        basic_auth_password: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize configuration.

        Parameters can be provided directly or will be loaded from environment
        variables if not provided. Direct parameters take precedence over
        environment variables.

        Args:
            base_url: Collibra base URL. If None, loads from COLLIBRA_BASE_URL env var.
            client_id: OAuth client ID. If None, loads from COLLIBRA_CLIENT_ID env var.
            client_secret: OAuth client secret. If None, loads from COLLIBRA_CLIENT_SECRET env var.
            basic_auth_username: Basic Auth username. If None, loads from COLLIBRA_BASIC_AUTH_USERNAME env var.
            basic_auth_password: Basic Auth password. If None, loads from COLLIBRA_BASIC_AUTH_PASSWORD env var.
            timeout: Request timeout in seconds. Defaults to 30.

        Raises:
            ValueError: If any required configuration value is missing after
                       checking both parameters and environment variables.
        """
        self.base_url = base_url or os.getenv("COLLIBRA_BASE_URL")
        self.client_id = client_id or os.getenv("COLLIBRA_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("COLLIBRA_CLIENT_SECRET")
        self.basic_auth_username = basic_auth_username or os.getenv("COLLIBRA_BASIC_AUTH_USERNAME")
        self.basic_auth_password = basic_auth_password or os.getenv("COLLIBRA_BASIC_AUTH_PASSWORD")
        self.timeout = timeout

        self._validate()

    def _validate(self) -> None:
        """
        Validate that required configuration values are present.

        Checks that base_url, client_id, and client_secret are all set.
        Raises ValueError with a descriptive message if any are missing.

        Raises:
            ValueError: If any required configuration value is missing.
        """
        if not self.base_url:
            raise ValueError(
                "Collibra base URL is required. "
                "Set COLLIBRA_BASE_URL environment variable or pass base_url parameter."
            )

        if not self.client_id:
            raise ValueError(
                "Collibra client ID is required. "
                "Set COLLIBRA_CLIENT_ID environment variable or pass client_id parameter."
            )

        if not self.client_secret:
            raise ValueError(
                "Collibra client secret is required. "
                "Set COLLIBRA_CLIENT_SECRET environment variable or pass client_secret parameter."
            )

    @classmethod
    def from_env(cls, timeout: int = 30) -> "CollibraConfig":
        """
        Create configuration from environment variables.

        This class method creates a CollibraConfig instance by loading all
        configuration values from environment variables. The .env file is
        automatically loaded if present.

        Required environment variables:
        - COLLIBRA_BASE_URL: Base URL of the Collibra instance
        - COLLIBRA_CLIENT_ID: OAuth client ID
        - COLLIBRA_CLIENT_SECRET: OAuth client secret

        Args:
            timeout: Request timeout in seconds. Defaults to 30.

        Returns:
            CollibraConfig instance configured from environment variables.

        Raises:
            ValueError: If any required environment variable is missing.

        Examples:
            >>> # Set environment variables first
            >>> import os
            >>> os.environ["COLLIBRA_BASE_URL"] = "https://instance.collibra.com"
            >>> os.environ["COLLIBRA_CLIENT_ID"] = "client_id"
            >>> os.environ["COLLIBRA_CLIENT_SECRET"] = "client_secret"
            >>>
            >>> # Load configuration
            >>> config = CollibraConfig.from_env(timeout=60)
        """
        return cls(timeout=timeout)

