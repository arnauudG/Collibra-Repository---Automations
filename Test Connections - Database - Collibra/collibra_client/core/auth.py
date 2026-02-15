"""
OAuth 2.0 authentication module for Collibra API.

This module handles token acquisition, storage, and refresh logic
following the OAuth 2.0 client credentials flow.
"""

import time
from dataclasses import dataclass
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from collibra_client.core.exceptions import (
    CollibraAuthenticationError,
    CollibraTokenError,
)


@dataclass
class TokenInfo:
    """
    Represents an OAuth access token and its metadata.

    This dataclass stores token information including the access token itself,
    token type, expiration time, and issue timestamp. It provides properties
    to check token expiration status.

    Attributes:
        access_token: The OAuth access token string.
        token_type: The token type (typically "Bearer").
        expires_in: Token expiration time in seconds from issue time.
        issued_at: Unix timestamp when the token was issued.

    Examples:
        >>> token_info = TokenInfo(
        ...     access_token="abc123",
        ...     token_type="Bearer",
        ...     expires_in=3600,
        ...     issued_at=time.time()
        ... )
        >>> print(f"Token expires at: {token_info.expires_at}")
        >>> print(f"Is expired: {token_info.is_expired}")
    """

    access_token: str
    token_type: str
    expires_in: int
    issued_at: float

    @property
    def is_expired(self) -> bool:
        """
        Check if the token has expired (with 60 second buffer).

        The buffer ensures tokens are refreshed before they actually expire,
        preventing race conditions where a token expires between check and use.

        Returns:
            True if the token is expired or will expire within 60 seconds,
            False otherwise.
        """
        buffer_seconds = 60
        expiration_time = self.issued_at + self.expires_in
        return time.time() >= (expiration_time - buffer_seconds)

    @property
    def expires_at(self) -> float:
        """
        Get the absolute expiration timestamp.

        Returns:
            Unix timestamp representing when the token expires.
        """
        return self.issued_at + self.expires_in


class CollibraAuthenticator:
    """
    Handles OAuth 2.0 client credentials authentication for Collibra API.

    This class manages the complete token lifecycle including acquisition,
    caching, validation, and automatic refresh when tokens expire. It implements
    the OAuth 2.0 client credentials flow as specified by Collibra's API.

    The authenticator automatically handles:
    - Token acquisition from Collibra's OAuth endpoint
    - Token caching to minimize API calls
    - Token expiration detection with buffer time
    - Automatic token refresh when expired
    - Retry logic for transient network failures

    Attributes:
        TOKEN_ENDPOINT: The OAuth token endpoint path.
        base_url: Base URL of the Collibra instance.
        client_id: OAuth client ID.
        client_secret: OAuth client secret.
        timeout: Request timeout in seconds.

    Examples:
        >>> authenticator = CollibraAuthenticator(
        ...     base_url="https://instance.collibra.com",
        ...     client_id="your_client_id",
        ...     client_secret="your_client_secret"
        ... )
        >>> token = authenticator.get_access_token()
        >>> print(f"Access token: {token[:20]}...")
    """

    TOKEN_ENDPOINT = "/rest/oauth/v2/token"

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        timeout: int = 30,
    ):
        """
        Initialize the authenticator.

        Args:
            base_url: Base URL of the Collibra instance (e.g., https://instance.collibra.com)
            client_id: OAuth client ID
            client_secret: OAuth client secret
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self._token: Optional[TokenInfo] = None

        # Configure session with retry strategy
        self._session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get a valid access token, refreshing if necessary.

        Args:
            force_refresh: Force token refresh even if current token is valid

        Returns:
            Valid access token string

        Raises:
            CollibraAuthenticationError: If token acquisition fails
        """
        if force_refresh or not self._token or self._token.is_expired:
            self._acquire_token()

        if not self._token:
            raise CollibraTokenError("Failed to acquire access token")

        return self._token.access_token

    def _acquire_token(self) -> None:
        """
        Acquire a new access token from Collibra OAuth endpoint.

        Raises:
            CollibraAuthenticationError: If token acquisition fails
        """
        token_url = f"{self.base_url}{self.TOKEN_ENDPOINT}"

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            response = self._session.post(
                token_url,
                data=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()

            token_data = response.json()
            self._token = TokenInfo(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=int(token_data.get("expires_in", 3600)),
                issued_at=time.time(),
            )

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None

            # Handle rate limiting (429) specially
            if status_code == 429:
                # If we have a cached token, try to use it even if slightly expired
                if self._token and not self._token.is_expired:
                    # Token is still valid, don't raise error
                    return
                # Otherwise, raise rate limit error with helpful message
                error_message = (
                    "Rate limit exceeded (429 Too Many Requests). "
                    "Too many token acquisition requests. "
                    "Please wait before retrying or reuse existing tokens."
                )
            else:
                error_message = f"Failed to acquire token: {e}"
                if e.response:
                    try:
                        error_body = e.response.json()
                        error_message = error_body.get("error_description", error_message)
                    except ValueError:
                        error_message = e.response.text or error_message

            raise CollibraAuthenticationError(
                error_message, status_code=status_code
            ) from e

        except requests.exceptions.RequestException as e:
            raise CollibraAuthenticationError(
                f"Network error during token acquisition: {e}"
            ) from e

        except (KeyError, ValueError) as e:
            raise CollibraTokenError(f"Invalid token response format: {e}") from e

    def invalidate_token(self) -> None:
        """
        Invalidate the current token, forcing a refresh on next request.

        This method clears the cached token, ensuring that the next call to
        `get_access_token()` will acquire a fresh token from the OAuth endpoint.

        This is useful when:
        - You want to force a token refresh
        - A token has been revoked
        - Testing token refresh logic

        Examples:
            >>> authenticator.invalidate_token()
            >>> # Next call will acquire a new token
            >>> token = authenticator.get_access_token()
        """
        self._token = None

    def get_token_info(self) -> Optional[TokenInfo]:
        """
        Get current token information (if available).

        Returns the TokenInfo object containing the current access token
        and its metadata. Returns None if no token has been acquired yet.

        Returns:
            TokenInfo object with token details, or None if no token exists.

        Examples:
            >>> token_info = authenticator.get_token_info()
            >>> if token_info:
            ...     print(f"Token expires in {token_info.expires_in} seconds")
        """
        return self._token

