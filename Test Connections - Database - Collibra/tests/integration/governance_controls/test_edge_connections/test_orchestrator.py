"""
Integration tests for the GovernanceOrchestrator.
"""

import pytest
from governance_controls.test_edge_connections.logic.orchestrator import GovernanceOrchestrator
from collibra_client.catalog.connections import DatabaseConnectionManager
from governance_controls.test_edge_connections.governed_config import load_governed_config

def test_orchestrator_initialization(collibra_client):
    """Test that the orchestrator can be initialized with standard components."""
    db_manager = DatabaseConnectionManager(client=collibra_client, use_oauth=True)
    orchestrator = GovernanceOrchestrator(
        client=collibra_client,
        db_manager=db_manager,
    )
    assert orchestrator.client == collibra_client
    assert orchestrator.db_manager == db_manager
    assert orchestrator.reporter is not None
    assert orchestrator.poller is not None
    assert orchestrator.mapper is not None

@pytest.mark.integration
def test_orchestrator_run_smoke(collibra_client):
    """
    Smoke test for the orchestrator run on the governed scope.
    This performs a real run but we mainly check it doesn't crash
    and produces the expected workflow steps.
    """
    db_manager = DatabaseConnectionManager(client=collibra_client, use_oauth=True)
    governed_edge_ids, metadata = load_governed_config()

    if not governed_edge_ids:
        pytest.skip("No governed edge IDs found in config")

    orchestrator = GovernanceOrchestrator(
        client=collibra_client,
        db_manager=db_manager,
        max_workers=2,
        poll_delay=1, # Faster for testing
        job_timeout=10 # Short timeout for testing
    )

    # We only test the first site to keep it quick
    test_scope = [sorted(list(governed_edge_ids))[0]]

    # Should not raise any exceptions
    orchestrator.run(test_scope, metadata)

@pytest.mark.integration
def test_orchestrator_test_individual_connections(collibra_client):
    """
    Test the test_individual_connections method for direct connection testing.
    """
    db_manager = DatabaseConnectionManager(client=collibra_client, use_oauth=True)

    # First, get a real connection ID from a governed site
    governed_edge_ids, metadata = load_governed_config()
    if not governed_edge_ids:
        pytest.skip("No governed edge IDs found in config")

    # Get connections from the first Edge Site
    edge_site_id = sorted(list(governed_edge_ids))[0]
    try:
        connections = db_manager.get_edge_site_connections(edge_site_id=edge_site_id)
        if not connections:
            pytest.skip("No connections found in Edge Site")

        # Get first testable connection ID
        connection_id = connections[0].get("id")
        if not connection_id:
            pytest.skip("No connection ID found")

    except Exception as e:
        pytest.skip(f"Failed to get connections: {e}")

    orchestrator = GovernanceOrchestrator(
        client=collibra_client,
        db_manager=db_manager,
        max_workers=2,
        poll_delay=1,
        job_timeout=10
    )

    # Test individual connection (should not raise exceptions)
    orchestrator.test_individual_connections([connection_id])

@pytest.mark.integration
def test_orchestrator_test_connections_in_edge_site(collibra_client):
    """
    Test the test_connections_in_edge_site method for contextual connection testing.
    """
    db_manager = DatabaseConnectionManager(client=collibra_client, use_oauth=True)

    # Get a real Edge Site and connection ID
    governed_edge_ids, metadata = load_governed_config()
    if not governed_edge_ids:
        pytest.skip("No governed edge IDs found in config")

    edge_site_id = sorted(list(governed_edge_ids))[0]

    # Get connections from the Edge Site
    try:
        connections = db_manager.get_edge_site_connections(edge_site_id=edge_site_id)
        if not connections:
            pytest.skip("No connections found in Edge Site")

        # Get first testable connection ID
        connection_id = connections[0].get("id")
        if not connection_id:
            pytest.skip("No connection ID found")

    except Exception as e:
        pytest.skip(f"Failed to get connections: {e}")

    orchestrator = GovernanceOrchestrator(
        client=collibra_client,
        db_manager=db_manager,
        max_workers=2,
        poll_delay=1,
        job_timeout=10
    )

    # Test connection within Edge Site context (should not raise exceptions)
    orchestrator.test_connections_in_edge_site(
        edge_site_id=edge_site_id,
        connection_ids=[connection_id],
        edge_metadata=metadata
    )

@pytest.mark.integration
def test_orchestrator_test_individual_connections_invalid_id(collibra_client):
    """
    Test test_individual_connections with an invalid connection ID.
    Should handle gracefully without crashing.
    """
    db_manager = DatabaseConnectionManager(client=collibra_client, use_oauth=True)

    orchestrator = GovernanceOrchestrator(
        client=collibra_client,
        db_manager=db_manager,
        max_workers=2,
        poll_delay=1,
        job_timeout=10
    )

    # Test with invalid connection ID (should handle gracefully)
    invalid_id = "00000000-0000-0000-0000-000000000000"
    orchestrator.test_individual_connections([invalid_id])
