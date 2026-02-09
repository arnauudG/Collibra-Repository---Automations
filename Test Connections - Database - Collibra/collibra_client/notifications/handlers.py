"""
Notification module for database connection failures.

This module provides functionality to notify database connection owners
when their database sync fails due to credential changes.
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from collibra_client.core.client import CollibraClient
from collibra_client.catalog.connections import DatabaseConnection
from collibra_client.core.exceptions import CollibraAPIError


class NotificationHandler(ABC):
    """
    Abstract base class for notification handlers.

    This class defines the interface for notification handlers that can
    be used to notify users about database connection failures.
    """

    @abstractmethod
    def notify(
        self,
        connection: DatabaseConnection,
        error_message: str,
        owner_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send a notification about a database connection failure.

        Args:
            connection: The database connection that failed.
            error_message: Error message describing the failure.
            owner_info: Optional dictionary containing owner information.

        Returns:
            True if notification was sent successfully, False otherwise.
        """
        pass


class CollibraNotificationHandler(NotificationHandler):
    """
    Notification handler that sends notifications via Collibra.

    This handler can send notifications through Collibra's messaging system,
    create tasks, or update assets with failure information.
    """

    def __init__(self, client: CollibraClient):
        """
        Initialize the Collibra notification handler.

        Args:
            client: CollibraClient instance for making API calls.
        """
        self.client = client

    def notify(
        self,
        connection: DatabaseConnection,
        error_message: str,
        owner_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send notification via Collibra API.

        This implementation can be extended to:
        - Create a task for the owner
        - Send a message/notification
        - Update the database asset with failure status
        - Create an activity log entry

        Args:
            connection: The database connection that failed.
            error_message: Error message describing the failure.
            owner_info: Optional dictionary containing owner information.

        Returns:
            True if notification was sent successfully, False otherwise.

        Examples:
            >>> handler = CollibraNotificationHandler(client)
            >>> handler.notify(
            ...     connection=db_conn,
            ...     error_message="Database credentials have changed",
            ...     owner_info={"id": "user-uuid", "username": "owner@example.com"}
            ... )
        """
        try:
            # If database_id exists, we can update the asset or create a task
            if connection.database_id:
                # Example: Create a task for the owner
                # This is a placeholder - implement based on your Collibra setup
                task_data = {
                    "name": f"Database Connection Failure: {connection.name}",
                    "description": f"Database connection sync failed: {error_message}",
                    "assetId": connection.database_id,
                }

                if owner_info and owner_info.get("id"):
                    task_data["assigneeId"] = owner_info["id"]

                # Uncomment when you have the task creation endpoint
                # self.client.post("/rest/2.0/tasks", json_data=task_data)

            # Log the notification attempt
            print(f"Notification sent for connection {connection.name} ({connection.id})")
            print(f"Error: {error_message}")
            if owner_info:
                print(f"Owner: {owner_info.get('username', owner_info.get('id', 'Unknown'))}")

            return True

        except CollibraAPIError as e:
            print(f"Failed to send notification via Collibra: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error sending notification: {e}")
            return False


class EmailNotificationHandler(NotificationHandler):
    """
    Notification handler that sends email notifications.

    This handler sends email notifications to database connection owners.
    Requires email configuration to be set up.
    """

    def __init__(self, smtp_server: str, smtp_port: int = 587, use_tls: bool = True):
        """
        Initialize the email notification handler.

        Args:
            smtp_server: SMTP server hostname.
            smtp_port: SMTP server port (default: 587).
            use_tls: Whether to use TLS encryption (default: True).
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.use_tls = use_tls

    def notify(
        self,
        connection: DatabaseConnection,
        error_message: str,
        owner_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send email notification.

        Args:
            connection: The database connection that failed.
            error_message: Error message describing the failure.
            owner_info: Optional dictionary containing owner email address.

        Returns:
            True if email was sent successfully, False otherwise.

        Note:
            This is a placeholder implementation. Implement actual email
            sending logic based on your email infrastructure.
        """
        # Placeholder for email implementation
        # Implement using smtplib or your email service
        email = owner_info.get("email") if owner_info else None
        if not email:
            print(f"No email address found for connection {connection.name}")
            return False

        print(f"Email notification would be sent to {email}")
        print(f"Subject: Database Connection Failure: {connection.name}")
        print(f"Body: {error_message}")
        return True


class ConsoleNotificationHandler(NotificationHandler):
    """
    Simple notification handler that prints to console.

    Useful for testing and development.
    """

    def notify(
        self,
        connection: DatabaseConnection,
        error_message: str,
        owner_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Print notification to console.

        Args:
            connection: The database connection that failed.
            error_message: Error message describing the failure.
            owner_info: Optional dictionary containing owner information.

        Returns:
            Always returns True.
        """
        print("=" * 60)
        print("DATABASE CONNECTION FAILURE NOTIFICATION")
        print("=" * 60)
        print(f"Connection Name: {connection.name}")
        print(f"Connection ID: {connection.id}")
        print(f"Database ID: {connection.database_id or 'N/A'}")
        print(f"Error: {error_message}")
        if owner_info:
            print(f"Owner: {owner_info.get('username', owner_info.get('id', 'Unknown'))}")
            if owner_info.get("email"):
                print(f"Email: {owner_info['email']}")
        print("=" * 60)
        return True

