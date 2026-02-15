"""
Main Collibra API client.

This module provides a high-level interface for interacting with
Collibra's REST API with automatic authentication handling.
"""

import json
from typing import Optional, Dict, Any, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from collibra_client.core.auth import CollibraAuthenticator
from collibra_client.core.exceptions import (
    CollibraAPIError,
    CollibraAuthenticationError,
)


class CollibraClient:
    """
    High-level client for Collibra REST API.

    This client provides a convenient interface for interacting with Collibra's
    REST API. It handles authentication automatically using OAuth 2.0 client
    credentials flow and provides methods for common HTTP operations.

    Key Features:
    - Automatic OAuth token management and refresh
    - Retry logic for transient failures
    - Comprehensive error handling with custom exceptions
    - Support for GET, POST, PUT, DELETE operations
    - Type hints for better IDE support

    The client uses dependency injection for the authenticator, allowing for
    easy testing and customization of authentication behavior.

    Attributes:
        API_VERSION: Default API version used by Collibra (currently "2.0").
        DEFAULT_TIMEOUT: Default request timeout in seconds (30).

    Examples:
        >>> from collibra_client import CollibraClient
        >>>
        >>> client = CollibraClient(
        ...     base_url="https://instance.collibra.com",
        ...     client_id="your_client_id",
        ...     client_secret="your_client_secret"
        ... )
        >>>
        >>> # Test connection
        >>> client.test_connection()
        >>>
        >>> # Make API calls
        >>> users = client.get("/rest/2.0/users")
        >>> current_user = client.get("/rest/2.0/users/current")
    """

    API_VERSION = "2.0"
    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        timeout: int = DEFAULT_TIMEOUT,
        authenticator: Optional[CollibraAuthenticator] = None,
    ):
        """
        Initialize the Collibra client.

        Args:
            base_url: Base URL of the Collibra instance
            client_id: OAuth client ID
            client_secret: OAuth client secret
            timeout: Request timeout in seconds
            authenticator: Optional pre-configured authenticator instance
                          (useful for dependency injection)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Use provided authenticator or create a new one
        self._authenticator = authenticator or CollibraAuthenticator(
            base_url=base_url,
            client_id=client_id,
            client_secret=client_secret,
            timeout=timeout,
        )

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

    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get request headers with authentication token.

        This private method constructs HTTP headers for API requests, including
        the Authorization header with the current access token. Additional headers
        can be merged in, with additional headers taking precedence.

        Args:
            additional_headers: Optional dictionary of additional headers to include.
                              These will override default headers if keys conflict.

        Returns:
            Dictionary containing all headers including Authorization, Content-Type,
            and Accept headers, merged with any additional headers provided.
        """
        token = self._authenticator.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if additional_headers:
            headers.update(additional_headers)

        return headers

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """
        Make an authenticated HTTP request to the Collibra API.

        This private method handles the low-level HTTP request logic including:
        - Automatic authentication token injection
        - Request retry logic for transient failures
        - Automatic token refresh on 401 errors
        - Comprehensive error handling and exception wrapping

        Args:
            method: HTTP method string (e.g., "GET", "POST", "PUT", "DELETE").
            endpoint: API endpoint path relative to base URL (e.g., "/rest/2.0/assets").
            params: Optional dictionary of query parameters to append to the URL.
            data: Optional request body data for form-encoded requests.
                 Ignored if json_data is provided.
            json_data: Optional dictionary to send as JSON in the request body.
            headers: Optional dictionary of additional HTTP headers to include.

        Returns:
            requests.Response object containing the API response.

        Raises:
            CollibraAPIError: If the API request fails (HTTP errors, network errors).
            CollibraAuthenticationError: If authentication fails after retry.
        """
        url = f"{self.base_url}{endpoint}"
        request_headers = self._get_headers(headers)

        # Prepare request kwargs
        request_kwargs = {
            "headers": request_headers,
            "timeout": self.timeout,
        }

        if params:
            request_kwargs["params"] = params

        if json_data:
            request_kwargs["json"] = json_data
        elif data:
            request_kwargs["data"] = data

        try:
            response = self._session.request(method, url, **request_kwargs)

            # Handle authentication errors - try refreshing token once
            if response.status_code == 401:
                self._authenticator.invalidate_token()
                request_headers = self._get_headers(headers)
                request_kwargs["headers"] = request_headers
                response = self._session.request(method, url, **request_kwargs)

            response.raise_for_status()
            return response

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            response_body = None

            if e.response:
                try:
                    response_body = e.response.json()
                    error_message = response_body.get(
                        "message", response_body.get("error", str(e))
                    )
                except (ValueError, json.JSONDecodeError):
                    response_body = e.response.text
                    error_message = response_body or str(e)
            else:
                error_message = str(e)

            raise CollibraAPIError(
                f"API request failed: {error_message}",
                status_code=status_code,
                response_body=response_body,
            )

        except requests.exceptions.RequestException as e:
            raise CollibraAPIError(f"Network error: {e}")

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a GET request to the Collibra API.

        This method performs an authenticated GET request to the specified
        endpoint. Authentication is handled automatically.

        Args:
            endpoint: API endpoint path (e.g., "/rest/2.0/users").
            params: Optional dictionary of query parameters to include in the request.
            headers: Optional dictionary of additional HTTP headers to include.

        Returns:
            JSON response parsed as a dictionary.

        Raises:
            CollibraAPIError: If the API request fails.
            CollibraAuthenticationError: If authentication fails.

        Examples:
            >>> # Get all users
            >>> users = client.get("/rest/2.0/users")
            >>>
            >>> # Get users with pagination
            >>> users = client.get("/rest/2.0/users", params={"limit": 10, "offset": 0})
            >>>
            >>> # Get current user
            >>> current_user = client.get("/rest/2.0/users/current")
        """
        response = self._make_request("GET", endpoint, params=params, headers=headers)
        return response.json()

    def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a POST request to the Collibra API.

        This method performs an authenticated POST request to the specified
        endpoint. You can send either JSON data or form-encoded data.

        Args:
            endpoint: API endpoint path (e.g., "/rest/2.0/assets").
            json_data: Optional dictionary to send as JSON in the request body.
            data: Optional dictionary or string to send as form-encoded data.
                  Ignored if json_data is provided.
            params: Optional dictionary of query parameters to include in the request.
            headers: Optional dictionary of additional HTTP headers to include.

        Returns:
            JSON response parsed as a dictionary.

        Raises:
            CollibraAPIError: If the API request fails.
            CollibraAuthenticationError: If authentication fails.

        Examples:
            >>> # Create a new asset
            >>> new_asset = client.post(
            ...     "/rest/2.0/assets",
            ...     json_data={"name": "My Asset", "domainId": "domain-uuid"}
            ... )
        """
        response = self._make_request(
            "POST",
            endpoint,
            json_data=json_data,
            data=data,
            params=params,
            headers=headers,
        )
        return response.json()

    def put(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a PUT request to the Collibra API.

        This method performs an authenticated PUT request to update a resource
        at the specified endpoint. You can send either JSON data or form-encoded data.

        Args:
            endpoint: API endpoint path (e.g., "/rest/2.0/assets/{assetId}").
            json_data: Optional dictionary to send as JSON in the request body.
            data: Optional dictionary or string to send as form-encoded data.
                  Ignored if json_data is provided.
            params: Optional dictionary of query parameters to include in the request.
            headers: Optional dictionary of additional HTTP headers to include.

        Returns:
            JSON response parsed as a dictionary.

        Raises:
            CollibraAPIError: If the API request fails.
            CollibraAuthenticationError: If authentication fails.

        Examples:
            >>> # Update an asset
            >>> updated_asset = client.put(
            ...     "/rest/2.0/assets/asset-uuid",
            ...     json_data={"name": "Updated Asset Name"}
            ... )
        """
        response = self._make_request(
            "PUT",
            endpoint,
            json_data=json_data,
            data=data,
            params=params,
            headers=headers,
        )
        return response.json()

    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a DELETE request to the Collibra API.

        This method performs an authenticated DELETE request to remove a resource
        at the specified endpoint.

        Args:
            endpoint: API endpoint path (e.g., "/rest/2.0/assets/{assetId}").
            params: Optional dictionary of query parameters to include in the request.
            headers: Optional dictionary of additional HTTP headers to include.

        Returns:
            JSON response parsed as a dictionary. Returns empty dictionary
            if the endpoint returns 204 No Content.

        Raises:
            CollibraAPIError: If the API request fails.
            CollibraAuthenticationError: If authentication fails.

        Examples:
            >>> # Delete an asset
            >>> result = client.delete("/rest/2.0/assets/asset-uuid")
        """
        response = self._make_request("DELETE", endpoint, params=params, headers=headers)
        try:
            return response.json()
        except ValueError:
            # Some DELETE endpoints return 204 No Content
            return {}

    def test_connection(self) -> bool:
        """
        Test the connection to Collibra API.

        Returns:
            True if connection is successful

        Raises:
            CollibraAPIError: If connection test fails
        """
        try:
            # Try to get user info or a simple endpoint
            self.get("/rest/2.0/users/current")
            return True
        except CollibraAPIError:
            raise

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the status of a job by its ID.

        This method retrieves the current status of an asynchronous job
        that was started by another API call (e.g., connection refresh).

        Args:
            job_id: UUID of the job to check.

        Returns:
            Dictionary containing job status information, including:
            - id: Job ID
            - status: Job status (e.g., "RUNNING", "SUCCESS", "FAILED")
            - progress: Progress percentage (0-100)
            - message: Status message
            - startDate: Job start timestamp
            - endDate: Job end timestamp (if completed)
            - error: Error details (if failed)

        Raises:
            CollibraAPIError: If the API request fails.

        Examples:
            >>> job_status = client.get_job_status("job-uuid")
            >>> print(f"Job status: {job_status['status']}")
            >>> print(f"Progress: {job_status.get('progress', 0)}%")
        """
        endpoint = f"/rest/jobs/v1/jobs/{job_id}"
        return self.get(endpoint)

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get user details by ID.

        This method retrieves detailed information about a user, including
        email address, username, and other user properties.

        Args:
            user_id: UUID of the user.

        Returns:
            Dictionary containing user information, including:
            - id: User ID
            - username: Username
            - email: Email address
            - firstName: First name
            - lastName: Last name
            - Other user properties

        Raises:
            CollibraAPIError: If the API request fails.

        Examples:
            >>> user = client.get_user("user-uuid")
            >>> print(f"User email: {user.get('email')}")
            >>> print(f"Username: {user.get('username')}")
        """
        endpoint = f"/rest/2.0/users/{user_id}"
        return self.get(endpoint)

