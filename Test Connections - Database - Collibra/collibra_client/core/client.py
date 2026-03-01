"""
Main Collibra API client.

This module provides a high-level interface for interacting with
Collibra's REST API with automatic authentication handling.
"""

import json
from typing import Any, Optional, Union

import requests
from collibra_client.core.auth import Authenticator, BasicAuthenticator, CollibraAuthenticator
from collibra_client.core.exceptions import (
    CollibraAPIError,
)
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        authenticator: Optional[Authenticator] = None,
        session_name: Optional[str] = None,
    ):
        """
        Initialize the Collibra client.

        You can authenticate using one of three methods:
        1. Provide a pre-configured authenticator instance
        2. Provide OAuth credentials (client_id and client_secret)
        3. Provide Basic Auth credentials (username and password)

        Args:
            base_url: Base URL of the Collibra instance
            client_id: OAuth client ID (for OAuth 2.0 authentication)
            client_secret: OAuth client secret (for OAuth 2.0 authentication)
            username: Username (for Basic Authentication)
            password: Password (for Basic Authentication)
            timeout: Request timeout in seconds
            authenticator: Optional pre-configured authenticator instance
                          (useful for dependency injection)
            session_name: Optional name for tagging valid tokens (OAuth only)

        Raises:
            ValueError: If no valid authentication credentials are provided

        Examples:
            OAuth 2.0:
            >>> client = CollibraClient(
            ...     base_url="https://instance.collibra.com",
            ...     client_id="your_client_id",
            ...     client_secret="your_client_secret"
            ... )

            Basic Auth:
            >>> client = CollibraClient(
            ...     base_url="https://instance.collibra.com",
            ...     username="your_username",
            ...     password="your_password"
            ... )
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session_name = session_name

        # Determine which authentication method to use
        if authenticator:
            # Use provided authenticator
            self._authenticator = authenticator
        elif client_id and client_secret:
            # Use OAuth 2.0
            self._authenticator = CollibraAuthenticator(
                base_url=base_url,
                client_id=client_id,
                client_secret=client_secret,
                timeout=timeout,
                session_name=self.session_name,
            )
        elif username and password:
            # Use Basic Authentication
            self._authenticator = BasicAuthenticator(
                username=username,
                password=password,
            )
        else:
            raise ValueError(
                "Authentication required. Provide either:\n"
                "  - client_id and client_secret (OAuth 2.0), or\n"
                "  - username and password (Basic Auth), or\n"
                "  - a pre-configured authenticator instance"
            )

        # Configure session with retry strategy
        self._session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=25,
            pool_maxsize=25,
        )
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def _get_headers(self, additional_headers: Optional[dict[str, str]] = None) -> dict[str, str]:
        """
        Get request headers with authentication.

        This private method constructs HTTP headers for API requests, including
        the Authorization header with the appropriate authentication method
        (OAuth Bearer token or Basic Auth). Additional headers can be merged in,
        with additional headers taking precedence.

        Args:
            additional_headers: Optional dictionary of additional headers to include.
                              These will override default headers if keys conflict.

        Returns:
            Dictionary containing all headers including Authorization, Content-Type,
            and Accept headers, merged with any additional headers provided.
        """
        auth_header = self._authenticator.get_auth_header()
        headers = {
            "Authorization": auth_header,
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
        params: Optional[dict[str, Any]] = None,
        data: Optional[Union[dict[str, Any], str]] = None,
        json_data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
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

            # Handle authentication errors - try refreshing credentials once
            if response.status_code == 401:
                self._authenticator.invalidate()
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
                    error_message = response_body.get("message", response_body.get("error", str(e)))
                except (ValueError, json.JSONDecodeError):
                    response_body = e.response.text
                    error_message = response_body or str(e)
            else:
                error_message = str(e)

            raise CollibraAPIError(
                f"API request failed: {error_message}",
                status_code=status_code,
                response_body=response_body,
            ) from e

        except requests.exceptions.RequestException as e:
            raise CollibraAPIError(f"Network error: {e}") from e

    def get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
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
        json_data: Optional[dict[str, Any]] = None,
        data: Optional[Union[dict[str, Any], str]] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
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

    def post_graphql(
        self,
        endpoint: str,
        query: str,
        variables: Optional[dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        Make a POST request with a GraphQL payload to the Collibra API.

        Args:
            endpoint: API endpoint path (e.g., "/edge/api/graphql").
            query: The GraphQL query or mutation string.
            variables: Optional dictionary of variables for the query.
            operation_name: Optional name of the operation to execute.
            headers: Optional dictionary of additional HTTP headers to include.

        Returns:
            JSON response parsed as a dictionary.

        Raises:
            CollibraAPIError: If the API request fails or returns GraphQL errors.
        """
        payload: dict[str, Any] = {"query": query}
        if variables is not None:
            payload["variables"] = variables
        if operation_name is not None:
            payload["operationName"] = operation_name

        response = self.post(endpoint, json_data=payload, headers=headers)

        if "errors" in response and response["errors"]:
            err_msg = response["errors"][0].get("message", "Unknown GraphQL Error")
            raise CollibraAPIError(
                f"GraphQL query failed with errors: {err_msg}",
                status_code=200,
                response_body=json.dumps(response),
            )

        return response

    def put(
        self,
        endpoint: str,
        json_data: Optional[dict[str, Any]] = None,
        data: Optional[Union[dict[str, Any], str]] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
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
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
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

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """
        Get the status of a job by its ID.

        This method retrieves the current status of an asynchronous job.
        It attempts the standard /rest/jobs/v1/jobs endpoint first.
        If a 404 is encountered, consider using get_edge_job_status() 
        in calling code.

        Args:
            job_id: UUID of the job to check.

        Returns:
            Dictionary containing job status information.
        """
        endpoint = f"/rest/jobs/v1/jobs/{job_id}"
        return self.get(endpoint)

    def get_edge_job_status(self, job_id: str) -> dict[str, Any]:
        """
        Get the status of an Edge job using the GraphQL API.

        This is used specifically for jobs initiated via the Edge GraphQL API
        (like connection tests) which may not be visible in the standard
        REST job endpoints.

        Args:
            job_id: UUID of the job to check.

        Returns:
            Dictionary containing job status (e.g., {"status": "SUCCESS", "message": "..."})
        """
        query = """
        query TestConnectionStatus($jobId: ID!) {
          job: jobById(id: $jobId) {
            status
            message
          }
        }
        """
        variables = {"jobId": job_id}
        result = self.post_graphql(
            "/edge/api/graphql", 
            query, 
            variables=variables, 
            operation_name="TestConnectionStatus"
        )
        # Unwrap the data part and return just the job info
        return result.get("data", {}).get("job") or {}

    def get_user(self, user_id: str) -> dict[str, Any]:
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
