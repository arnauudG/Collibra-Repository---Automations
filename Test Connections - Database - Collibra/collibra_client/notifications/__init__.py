"""
Notification system for database connection failures.

This module provides functionality to notify database connection owners
when their database sync fails due to credential changes.
"""

from collibra_client.notifications.handlers import (
    NotificationHandler,
    CollibraNotificationHandler,
    ConsoleNotificationHandler,
    EmailNotificationHandler,
)
from collibra_client.notifications.owner import get_connection_owner

__all__ = [
    "NotificationHandler",
    "CollibraNotificationHandler",
    "ConsoleNotificationHandler",
    "EmailNotificationHandler",
    "get_connection_owner",
]

