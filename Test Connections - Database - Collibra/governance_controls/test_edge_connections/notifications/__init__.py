"""
Notification system for database connection failures.

This module provides functionality to notify database connection owners
when their database connection refresh fails (e.g. due to credential changes).
"""

from governance_controls.test_edge_connections.notifications.handlers import (
    CollibraNotificationHandler,
    ConsoleNotificationHandler,
    EmailNotificationHandler,
    NotificationHandler,
)
from governance_controls.test_edge_connections.notifications.owner import get_connection_owner

__all__ = [
    "NotificationHandler",
    "CollibraNotificationHandler",
    "ConsoleNotificationHandler",
    "EmailNotificationHandler",
    "get_connection_owner",
]

