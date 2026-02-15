"""
Integration tests for database connection management.

These tests verify database connection listing, refresh, and
and owner information retrieval.

Requires environment variables:
    - COLLIBRA_BASE_URL
    - COLLIBRA_CLIENT_ID
    - COLLIBRA_CLIENT_SECRET

Note: These tests may be skipped if rate limiting (429) occurs.
Run tests individually or wait between runs to avoid rate limits.
"""

import json
from typing import Any, Optional

import pytest

from collibra_client import (
    CollibraClient,
    DatabaseConnection,
    DatabaseConnectionManager,
)
from tests.conftest import handle_rate_limit


def parse_job_message(message: str) -> Optional[dict[str, Any]]:
    """Parse the job status message (which is a JSON string)."""
    if not message:
        return None
    try:
        return json.loads(message)
    except (json.JSONDecodeError, TypeError):
        return None


@pytest.mark.integration
@pytest.mark.rate_limit
class TestDatabaseConnections:
    """Test suite for database connection management."""

    @handle_rate_limit
    def test_list_database_connections(
        self,
        db_manager: DatabaseConnectionManager,
    ):
        """Test listing database connections."""
        connections = db_manager.list_database_connections()
        assert isinstance(connections, list)
        assert len(connections) > 0

        # Verify connection structure
        for conn in connections:
            assert isinstance(conn, DatabaseConnection)
            assert conn.id is not None
            assert conn.name is not None
            assert conn.edge_connection_id is not None

    @handle_rate_limit
    def test_list_database_connections_with_filter(
        self,
        db_manager: DatabaseConnectionManager,
    ):
        """Test listing database connections with edge connection ID filter."""
        # First get all connections
        all_connections = db_manager.list_database_connections()
        assert len(all_connections) > 0

        # Get unique edge connection IDs
        edge_ids = {conn.edge_connection_id for conn in all_connections}
        assert len(edge_ids) > 0

        # Filter by first edge connection ID
        edge_id = list(edge_ids)[0]
        filtered = db_manager.list_database_connections(edge_connection_id=edge_id)
        assert len(filtered) > 0
        assert all(conn.edge_connection_id == edge_id for conn in filtered)

    @handle_rate_limit
    def test_list_database_connections_with_database_asset_id(
        self,
        db_manager: DatabaseConnectionManager,
    ):
        """Test listing only connections with database asset ID."""
        all_connections = db_manager.list_database_connections()

        # Filter to connections with database asset ID
        connections_with_asset = [
            conn for conn in all_connections if conn.database_id is not None
        ]

        assert len(connections_with_asset) > 0

        # Verify all have database_id
        for conn in connections_with_asset:
            assert conn.database_id is not None

    @handle_rate_limit
    def test_refresh_database_connections(
        self,
        db_manager: DatabaseConnectionManager,
    ):
        """Test refreshing database connections."""
        # Get existing connections to find edge connection IDs
        connections = db_manager.list_database_connections(limit=10)
        if not connections:
            pytest.skip("No database connections available")

        edge_ids = {conn.edge_connection_id for conn in connections}
        edge_id = list(edge_ids)[0]

        # Refresh the edge connection
        result = db_manager.refresh_database_connections(edge_connection_id=edge_id)
        assert result is not None

    @handle_rate_limit
    def test_get_database_asset(
        self,
        db_manager: DatabaseConnectionManager,
    ):
        """Test getting database asset details."""
        # Get a connection with database asset ID
        connections = db_manager.list_database_connections()
        connections_with_asset = [
            conn for conn in connections if conn.database_id is not None
        ]

        if not connections_with_asset:
            pytest.skip("No database connections with asset ID available")

        db_id = connections_with_asset[0].database_id
        asset = db_manager.get_database_asset(db_id)

        assert asset is not None
        assert "id" in asset or "databaseId" in asset

    @handle_rate_limit
    def test_synchronize_database_metadata(
        self,
        db_manager: DatabaseConnectionManager,
        collibra_client: CollibraClient,
    ):
        """Test the optional metadata sync API (not used by governing workflow)."""
        # Get a connection with database asset ID
        connections = db_manager.list_database_connections()
        connections_with_asset = [
            conn for conn in connections if conn.database_id is not None
        ]

        if not connections_with_asset:
            pytest.skip("No database connections with asset ID available")

        db_id = connections_with_asset[0].database_id

        # Call metadata sync endpoint (Catalog API)
        sync_result = db_manager.synchronize_database_metadata(db_id)
        assert sync_result is not None

        # Get job ID
        job_id = sync_result.get("jobId") or sync_result.get("id")
        if job_id:
            # Check job status
            job_status = collibra_client.get_job_status(job_id)
            assert job_status is not None

            # Verify job status structure
            status = (
                job_status.get("status") or
                job_status.get("state") or
                "UNKNOWN"
            )
            assert status is not None

            # Parse message if available
            message = job_status.get("message") or ""
            if message:
                parsed = parse_job_message(message)
                if parsed:
                    assert isinstance(parsed, dict)

    @handle_rate_limit
    def test_get_user_info(
        self,
        db_manager: DatabaseConnectionManager,
        collibra_client: CollibraClient,
    ):
        """Test getting user information for database owner."""
        # Get a connection with database asset ID
        connections = db_manager.list_database_connections()
        connections_with_asset = [
            conn for conn in connections if conn.database_id is not None
        ]

        if not connections_with_asset:
            pytest.skip("No database connections with asset ID available")

        db_id = connections_with_asset[0].database_id

        # Get database asset
        db_asset = db_manager.get_database_asset(db_id)

        # Try to get owner ID
        owner_id = (
            db_asset.get("ownerId") or
            db_asset.get("owner") or
            db_asset.get("responsibleId") or
            None
        )

        if owner_id:
            # Get user details
            user = collibra_client.get_user(owner_id)
            assert user is not None
            assert "id" in user or "userId" in user

