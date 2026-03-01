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

    Authentication methods (choose one):
    - OAuth 2.0: Provide client_id and client_secret
    - Basic Auth: Provide username and password

    Attributes:
        base_url: Base URL of the Collibra instance.
        client_id: OAuth client ID for authentication (OAuth 2.0).
        client_secret: OAuth client secret for authentication (OAuth 2.0).
        username: Username for Basic Authentication.
        password: Password for Basic Authentication.
        timeout: Request timeout in seconds (default: 30).

    Examples:
        >>> # OAuth from environment variables
        >>> config = CollibraConfig.from_env()
        >>>
        >>> # OAuth direct initialization
        >>> config = CollibraConfig(
        ...     base_url="https://instance.collibra.com",
        ...     client_id="client_id",
        ...     client_secret="client_secret",
        ...     timeout=60
        ... )
        >>>
        >>> # Basic Auth direct initialization
        >>> config = CollibraConfig(
        ...     base_url="https://instance.collibra.com",
        ...     username="your_username",
        ...     password="your_password"
        ... )
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize configuration.

        Parameters can be provided directly or will be loaded from environment
        variables if not provided. Direct parameters take precedence over
        environment variables.

        You must provide either OAuth credentials (client_id + client_secret)
        OR Basic Auth credentials (username + password).

        Args:
            base_url: Collibra base URL. If None, loads from COLLIBRA_BASE_URL env var.
            client_id: OAuth client ID. If None, loads from COLLIBRA_CLIENT_ID env var.
            client_secret: OAuth client secret. If None, loads from COLLIBRA_CLIENT_SECRET env var.
            username: Username for Basic Auth. If None, loads from COLLIBRA_USERNAME env var.
            password: Password for Basic Auth. If None, loads from COLLIBRA_PASSWORD env var.
            timeout: Request timeout in seconds. Defaults to 30.

        Raises:
            ValueError: If any required configuration value is missing after
                       checking both parameters and environment variables.
        """
        self.base_url = base_url or os.getenv("COLLIBRA_BASE_URL")
        self.client_id = client_id or os.getenv("COLLIBRA_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("COLLIBRA_CLIENT_SECRET")
        self.username = username or os.getenv("COLLIBRA_USERNAME")
        self.password = password or os.getenv("COLLIBRA_PASSWORD")
        self.timeout = timeout

        self._validate()

    def _validate(self) -> None:
        """
        Validate that required configuration values are present.

        Checks that base_url is set and that either OAuth credentials
        (client_id + client_secret) OR Basic Auth credentials (username + password)
        are provided.

        Raises:
            ValueError: If any required configuration value is missing.
        """
        if not self.base_url:
            raise ValueError(
                "Collibra base URL is required. "
                "Set COLLIBRA_BASE_URL environment variable or pass base_url parameter."
            )

        # Check for partial credentials first (more specific errors)
        if self.client_id and not self.client_secret:
            raise ValueError(
                "Incomplete OAuth credentials: client secret is missing. "
                "Both client_id and client_secret are required for OAuth 2.0."
            )

        if self.client_secret and not self.client_id:
            raise ValueError(
                "Incomplete OAuth credentials: client ID is missing. "
                "Both client_id and client_secret are required for OAuth 2.0."
            )

        if self.username and not self.password:
            raise ValueError(
                "Incomplete Basic Auth credentials: password is missing. "
                "Both username and password are required for Basic Authentication."
            )

        if self.password and not self.username:
            raise ValueError(
                "Incomplete Basic Auth credentials: username is missing. "
                "Both username and password are required for Basic Authentication."
            )

        # Check if any complete credential set is provided
        has_oauth = self.client_id and self.client_secret
        has_basic = self.username and self.password

        if not has_oauth and not has_basic:
            raise ValueError(
                "Authentication credentials required. Provide either:\n"
                "  OAuth 2.0:\n"
                "    - COLLIBRA_CLIENT_ID and COLLIBRA_CLIENT_SECRET, or\n"
                "    - client_id and client_secret parameters\n"
                "  Basic Auth:\n"
                "    - COLLIBRA_USERNAME and COLLIBRA_PASSWORD, or\n"
                "    - username and password parameters"
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

        Authentication (choose one method):
        - OAuth 2.0: COLLIBRA_CLIENT_ID and COLLIBRA_CLIENT_SECRET
        - Basic Auth: COLLIBRA_USERNAME and COLLIBRA_PASSWORD

        Args:
            timeout: Request timeout in seconds. Defaults to 30.

        Returns:
            CollibraConfig instance configured from environment variables.

        Raises:
            ValueError: If any required environment variable is missing.

        Examples:
            >>> # OAuth 2.0
            >>> import os
            >>> os.environ["COLLIBRA_BASE_URL"] = "https://instance.collibra.com"
            >>> os.environ["COLLIBRA_CLIENT_ID"] = "client_id"
            >>> os.environ["COLLIBRA_CLIENT_SECRET"] = "client_secret"
            >>> config = CollibraConfig.from_env()
            >>>
            >>> # Basic Auth
            >>> os.environ["COLLIBRA_BASE_URL"] = "https://instance.collibra.com"
            >>> os.environ["COLLIBRA_USERNAME"] = "username"
            >>> os.environ["COLLIBRA_PASSWORD"] = "password"
            >>> config = CollibraConfig.from_env()
        """
        return cls(timeout=timeout)
