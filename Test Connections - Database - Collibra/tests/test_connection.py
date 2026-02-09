"""
Integration tests for Collibra client connection.

These tests verify that the client can successfully authenticate
and connect to a Collibra instance.

Requires environment variables:
    - COLLIBRA_BASE_URL
    - COLLIBRA_CLIENT_ID
    - COLLIBRA_CLIENT_SECRET
"""

import pytest
from collibra_client import (
    CollibraClient,
    CollibraAuthenticationError,
    CollibraAPIError,
)
from tests.conftest import handle_rate_limit


@pytest.mark.integration
@pytest.mark.rate_limit
class TestConnection:
    """Test suite for Collibra client connection."""

    def test_client_initialization(self, collibra_client: CollibraClient):
        """Test that the client can be initialized."""
        assert collibra_client is not None
        assert collibra_client.base_url is not None
        assert collibra_client.timeout > 0

    @handle_rate_limit
    def test_connection_success(self, collibra_client: CollibraClient):
        """
        Test that the client can successfully connect to Collibra.

        This test verifies:
        - OAuth authentication works
        - API endpoint is reachable
        - Token is properly acquired and used
        """
        result = collibra_client.test_connection()
        assert result is True

    @handle_rate_limit
    def test_get_current_user(self, collibra_client: CollibraClient):
        """
        Test retrieving current user information.

        This verifies that:
        - Authentication token is valid
        - API calls work correctly
        - Response parsing works
        """
        user_info = collibra_client.get("/rest/2.0/users/current")
        
        assert user_info is not None
        assert isinstance(user_info, dict)
        # Verify common user fields exist
        assert "id" in user_info or "username" in user_info

    @handle_rate_limit
    def test_authentication_token_acquired(self, collibra_client: CollibraClient):
        """Test that authentication token is properly acquired."""
        # Force a token acquisition by making a request
        collibra_client.get("/rest/2.0/users/current")
        
        # Check that token info is available
        token_info = collibra_client._authenticator.get_token_info()
        assert token_info is not None
        assert token_info.access_token is not None
        assert len(token_info.access_token) > 0
        assert token_info.token_type == "Bearer"

    @handle_rate_limit
    def test_token_refresh_on_expiry(self, collibra_client: CollibraClient):
        """
        Test that token is automatically refreshed when expired.

        This test invalidates the current token and verifies
        that a new token is acquired on the next request.
        """
        # Get initial token
        initial_token = collibra_client._authenticator.get_access_token()
        
        # Invalidate token
        collibra_client._authenticator.invalidate_token()
        
        # Make a request - should automatically acquire new token
        collibra_client.get("/rest/2.0/users/current")
        
        # Verify new token was acquired
        new_token = collibra_client._authenticator.get_access_token()
        assert new_token is not None
        assert new_token != initial_token or initial_token is None

    @handle_rate_limit
    def test_get_request_with_params(self, collibra_client: CollibraClient):
        """Test GET request with query parameters."""
        # Test with pagination parameters
        response = collibra_client.get(
            "/rest/2.0/users",
            params={"limit": 5, "offset": 0}
        )
        
        assert response is not None
        assert isinstance(response, dict)
        # Collibra API typically returns results in a 'results' field
        if "results" in response:
            assert isinstance(response["results"], list)

    @handle_rate_limit
    def test_error_handling_invalid_endpoint(self, collibra_client: CollibraClient):
        """Test error handling for invalid API endpoint."""
        with pytest.raises(CollibraAPIError) as exc_info:
            collibra_client.get("/rest/2.0/invalid-endpoint-that-does-not-exist")
        
        # Verify error is raised and contains error message
        assert "404" in str(exc_info.value) or exc_info.value.status_code == 404
        # Status code may be None if error occurs before response, but error message should contain info

    @handle_rate_limit
    def test_connection_with_fresh_client(self, collibra_client_fresh: CollibraClient):
        """Test connection using a fresh client instance."""
        result = collibra_client_fresh.test_connection()
        assert result is True


@pytest.mark.integration
@pytest.mark.rate_limit
class TestAuthentication:
    """Test suite for authentication functionality."""

    @handle_rate_limit
    def test_authenticator_token_management(self, collibra_client: CollibraClient):
        """Test token management in the authenticator."""
        authenticator = collibra_client._authenticator
        
        # Get token
        token1 = authenticator.get_access_token()
        assert token1 is not None
        
        # Get token again - should return cached token
        token2 = authenticator.get_access_token()
        assert token2 == token1
        
        # Force refresh - may hit rate limit, decorator will handle it
        token3 = authenticator.get_access_token(force_refresh=True)
        assert token3 is not None
        # Token might be the same if not expired, but should be valid

    @handle_rate_limit
    def test_token_info_properties(self, collibra_client: CollibraClient):
        """Test TokenInfo properties and expiration logic."""
        # Make a request to acquire token
        collibra_client.get("/rest/2.0/users/current")
        
        token_info = collibra_client._authenticator.get_token_info()
        assert token_info is not None
        assert token_info.access_token is not None
        assert token_info.token_type == "Bearer"
        assert token_info.expires_in > 0
        assert token_info.issued_at > 0
        assert token_info.expires_at > token_info.issued_at
        # Token should not be expired immediately after acquisition
        assert token_info.is_expired is False

