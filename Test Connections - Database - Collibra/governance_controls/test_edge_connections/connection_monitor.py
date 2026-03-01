"""
Connection monitoring use case logic.

This module encapsulates the business logic for testing database
connections by triggering catalog refreshes, evaluating failure semantics,
and notifying owners using provided notification handlers.
"""

import logging
from typing import Any, Optional

from collibra_client.catalog.connections import DatabaseConnection, DatabaseConnectionManager
from collibra_client.core.exceptions import CollibraAPIError
from governance_controls.test_edge_connections.notifications.handlers import NotificationHandler
from governance_controls.test_edge_connections.notifications.owner import get_connection_owner

logger = logging.getLogger(__name__)


class ConnectionMonitor:
    """
    Business logic for monitoring and testing database connections.
    
    This class ties together the DatabaseConnectionManager and notification
    mechanisms to provide high-level testing features and alert workflows
    when connections become invalid.
    """

    def __init__(
        self,
        db_manager: DatabaseConnectionManager,
        notification_handler: Optional[NotificationHandler] = None,
    ):
        """
        Initialize the connection monitor.
        
        Args:
            db_manager: Manager for interacting with catalog database connections.
            notification_handler: Optional handler for dispatching failure notifications.
        """
        self.db_manager = db_manager
        self.notification_handler = notification_handler

    def test_connection(self, connection_id: str) -> dict[str, Any]:
        """
        Test a database connection by attempting to refresh it.
        
        If the refresh fails due to credential issues or timeouts, it indicates
        the connection is no longer valid.
        
        Args:
            connection_id: UUID of the database connection to test.
            
        Returns:
            Dictionary containing test results.
        """
        connection = self.db_manager.get_database_connection_by_id(connection_id)
        if not connection:
            return {
                "success": False,
                "message": f"Database connection {connection_id} not found",
                "connection_id": connection_id,
            }

        try:
            # Attempt to test the connection using its edge ID via GraphQL
            job_id = self.db_manager.test_edge_connection(
                edge_connection_id=connection.edge_connection_id
            )
            return {
                "success": True,
                "message": "Database connection test job submitted successfully",
                "job_id": job_id,
                "connection_id": connection_id,
                "connection_name": connection.name,
            }
        except CollibraAPIError as e:
            # Heuristic to detect authentication/credential related errors
            error_message = str(e).lower()
            is_credential_error = any(
                keyword in error_message
                for keyword in ["authentication", "credential", "password", "unauthorized", "forbidden"]
            )

            return {
                "success": False,
                "message": f"Database connection test failed: {e}",
                "connection_id": connection_id,
                "connection_name": connection.name,
                "error": str(e),
                "status_code": e.status_code,
                "is_credential_error": is_credential_error,
            }

    def test_and_notify(self, connection_id: str) -> dict[str, Any]:
        """
        Convenience method to test a connection and immediately notify the owner if it fails.
        
        Args:
            connection_id: UUID of the database connection.
            
        Returns:
            The test result dictionary.
            
        Raises:
            ValueError: If a notification_handler is not configured.
        """
        if not self.notification_handler:
            raise ValueError(
                "ConnectionMonitor must be initialized with a NotificationHandler "
                "to use test_and_notify()."
            )

        result = self.test_connection(connection_id)
        
        if not result["success"]:
            # Retrieve the connection object and its owner
            connection = self.db_manager.get_database_connection_by_id(connection_id)
            if connection:
                owner = get_connection_owner(self.db_manager.client, connection)
                self.notification_handler.notify(connection, result["message"], owner)
            else:
                logger.warning("Could not retrieve connection %s for notification.", connection_id)

        return result

    def test_site_connections(self, site_id: str) -> list[dict[str, Any]]:
        """
        Fetch and test all database connections hosted on a specific Edge Site.
        
        This method automates the discovery of nested connections and triggers
        sequential testing for each one found.
        
        Args:
            site_id: UUID of the Edge Site.
            
        Returns:
            List of test result dictionaries for all nested connections.
            
        Raises:
            CollibraAPIError: If the site connection discovery fails.
        """
        logger.info("Discovering connections for Edge Site: %s", site_id)
        connections = self.db_manager.get_edge_site_connections(site_id)

        if not connections:
            logger.warning("No connections found for Edge Site %s", site_id)
            return []

        logger.info("Found %d connections. Starting batch testing...", len(connections))

        results = []
        for conn_dict in connections:
            conn_id = conn_dict.get("id")
            if not conn_id:
                continue

            logger.info("Testing connection: %s (%s)", conn_dict.get("name"), conn_id)
            result = self.test_connection(conn_id)
            results.append(result)
            
        return results
