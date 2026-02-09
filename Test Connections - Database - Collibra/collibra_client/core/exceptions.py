"""
Custom exceptions for Collibra client operations.

This module defines a hierarchy of custom exceptions that provide
detailed error information for different failure scenarios in the
Collibra client library.
"""


class CollibraClientError(Exception):
    """
    Base exception for all Collibra client errors.

    All exceptions raised by the Collibra client inherit from this class,
    allowing for broad exception handling if needed.

    Examples:
        >>> try:
        ...     client.get("/rest/2.0/invalid")
        ... except CollibraClientError as e:
        ...     print(f"Collibra error: {e}")
    """

    pass


class CollibraAuthenticationError(CollibraClientError):
    """
    Raised when authentication fails.

    This exception is raised when OAuth token acquisition fails or
    when authentication credentials are invalid.

    Attributes:
        status_code: HTTP status code from the authentication request, if available.
        message: Error message describing the authentication failure.

    Examples:
        >>> try:
        ...     client = CollibraClient(base_url="...", client_id="invalid", client_secret="...")
        ...     client.test_connection()
        ... except CollibraAuthenticationError as e:
        ...     print(f"Auth failed with status {e.status_code}: {e}")
    """

    def __init__(self, message: str, status_code: int = None):
        """
        Initialize authentication error.

        Args:
            message: Error message describing the authentication failure.
            status_code: Optional HTTP status code from the authentication request.
        """
        super().__init__(message)
        self.status_code = status_code


class CollibraAPIError(CollibraClientError):
    """
    Raised when API requests fail.

    This exception is raised when API requests to Collibra fail,
    including HTTP errors, network errors, and invalid responses.

    Attributes:
        status_code: HTTP status code from the failed request, if available.
        response_body: Response body from the failed request, if available.
        message: Error message describing the API failure.

    Examples:
        >>> try:
        ...     client.get("/rest/2.0/nonexistent-resource")
        ... except CollibraAPIError as e:
        ...     print(f"API error {e.status_code}: {e}")
        ...     if e.response_body:
        ...         print(f"Response: {e.response_body}")
    """

    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        """
        Initialize API error.

        Args:
            message: Error message describing the API failure.
            status_code: Optional HTTP status code from the failed request.
            response_body: Optional response body from the failed request.
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class CollibraTokenError(CollibraAuthenticationError):
    """
    Raised when token operations fail.

    This exception is raised when token acquisition, validation,
    or parsing fails. It is a subclass of CollibraAuthenticationError
    to maintain the exception hierarchy.

    Examples:
        >>> try:
        ...     authenticator.get_access_token()
        ... except CollibraTokenError as e:
        ...     print(f"Token error: {e}")
    """

    pass

