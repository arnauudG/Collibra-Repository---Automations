"""
Owner information retrieval for database connections.

This module provides functionality to retrieve owner information
for database connections from Collibra assets.
"""

from typing import Any, Optional

from collibra_client.catalog.connections import DatabaseConnection
from collibra_client.core.client import CollibraClient
from collibra_client.core.exceptions import CollibraAPIError


def get_connection_owner(
    client: CollibraClient,
    connection: DatabaseConnection,
) -> Optional[dict[str, Any]]:
    """
    Get the owner information for a database connection.

    This function retrieves owner information from the linked Database asset
    using the Catalog Database API, which returns ownerIds as an array.
    Cataloged databases always have one or several owners.

    Args:
        client: CollibraClient instance for making API calls.
        connection: DatabaseConnection to get owner for.

    Returns:
        Dictionary containing owner information with keys:
        - id: Owner user ID (first owner from ownerIds array)
        - username: Owner username
        - email: Owner email address
        - fullName: Owner full name
        Returns None if owner cannot be determined.

    Examples:
        >>> from collibra_client import CollibraClient, get_connection_owner
        >>> owner = get_connection_owner(client, db_connection)
        >>> if owner:
        ...     print(f"Owner: {owner.get('username')}")
        ...     print(f"Email: {owner.get('email')}")
    """
    if not connection.database_id:
        return None

    try:
        # Use Catalog Database API to get database asset
        # This API returns ownerIds (array) per API documentation
        from collibra_client.catalog import DatabaseConnectionManager

        db_manager = DatabaseConnectionManager(client=client, use_oauth=True)
        db_asset = db_manager.get_database_asset(connection.database_id)

        # Catalog Database API returns ownerIds as an array
        owner_ids = db_asset.get("ownerIds")

        if not owner_ids or not isinstance(owner_ids, list) or len(owner_ids) == 0:
            return None

        # Use the first owner from the array
        owner_id = owner_ids[0]

        # Get user details
        try:
            user = client.get_user(owner_id)
            return {
                "id": user.get("id"),
                "username": user.get("username"),
                "email": user.get("email") or user.get("emailAddress"),
                "fullName": user.get("fullName") or (
                    f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()
                ),
            }
        except CollibraAPIError:
            # Return at least the owner ID if we can't get full details
            return {"id": owner_id}

    except CollibraAPIError:
        # Asset not found or other error
        return None

    return None

