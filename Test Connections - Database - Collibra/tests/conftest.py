"""
Pytest configuration and shared fixtures.
"""

from collections.abc import Generator
from functools import wraps

import pytest

from collibra_client import (
    CollibraClient,
    CollibraConfig,
    DatabaseConnectionManager,
)
from collibra_client.core.exceptions import CollibraAuthenticationError


def handle_rate_limit(func):
    """
    Decorator to handle rate limit errors in tests.

    If a test raises CollibraAuthenticationError with a 429 status code,
    the test will be skipped instead of failing.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CollibraAuthenticationError as e:
            if "429" in str(e) or "Rate limit" in str(e) or "Too Many Requests" in str(e) or (hasattr(e, 'status_code') and e.status_code == 429):
                pytest.skip(f"Rate limited: {e}")
            raise
    return wrapper


@pytest.fixture(scope="session")
def collibra_config() -> CollibraConfig:
    """
    Load Collibra configuration from environment variables.

    This fixture reads configuration from environment variables:
    - COLLIBRA_BASE_URL
    - COLLIBRA_CLIENT_ID
    - COLLIBRA_CLIENT_SECRET

    Raises:
        ValueError: If required environment variables are missing
    """
    try:
        return CollibraConfig.from_env()
    except ValueError as e:
        pytest.skip(f"Missing required environment variables: {e}")


@pytest.fixture(scope="session")
def collibra_client(collibra_config: CollibraConfig) -> CollibraClient:
    """
    Create a Collibra client instance for testing.

    This fixture creates a client using configuration from environment variables.
    The client is shared across all tests in the session. The token is acquired
    once and reused across all tests to avoid rate limiting.

    Args:
        collibra_config: Configuration fixture

    Returns:
        Configured CollibraClient instance
    """
    import time

    client = CollibraClient(
        base_url=collibra_config.base_url,
        client_id=collibra_config.client_id,
        client_secret=collibra_config.client_secret,
        timeout=collibra_config.timeout,
    )
    # Pre-acquire token to avoid rate limiting in tests
    # Retry with exponential backoff if rate limited
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client._authenticator.get_access_token()
            break  # Success, exit retry loop
        except Exception as e:
            if "429" in str(e) or "Rate limit" in str(e):
                if attempt < max_retries - 1:
                    # Exponential backoff: 2^attempt seconds
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
            # If not rate limit or max retries reached, let it fail
            # Tests will handle the error appropriately
            break
    return client


@pytest.fixture
def collibra_client_fresh(collibra_config: CollibraConfig) -> Generator[CollibraClient, None, None]:
    """
    Create a fresh Collibra client instance for each test.

    This fixture creates a new client for each test, ensuring isolation.
    Useful for tests that modify client state.

    Args:
        collibra_config: Configuration fixture

    Yields:
        Fresh CollibraClient instance
    """
    client = CollibraClient(
        base_url=collibra_config.base_url,
        client_id=collibra_config.client_id,
        client_secret=collibra_config.client_secret,
        timeout=collibra_config.timeout,
    )
    yield client
    # Cleanup if needed
    if hasattr(client, "_authenticator"):
        client._authenticator.invalidate_token()


@pytest.fixture(scope="session")
def db_manager(collibra_client: CollibraClient) -> DatabaseConnectionManager:
    """
    Create a DatabaseConnectionManager instance for testing.

    This fixture creates a DatabaseConnectionManager using the shared
    CollibraClient instance. The manager uses OAuth authentication.

    Args:
        collibra_client: CollibraClient fixture

    Returns:
        Configured DatabaseConnectionManager instance
    """
    return DatabaseConnectionManager(
        client=collibra_client,
        use_oauth=True,
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require actual Collibra credentials)"
    )
    config.addinivalue_line(
        "markers", "rate_limit: marks tests that may be skipped due to rate limiting"
    )

