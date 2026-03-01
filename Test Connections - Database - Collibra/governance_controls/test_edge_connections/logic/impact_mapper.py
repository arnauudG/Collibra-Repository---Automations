"""
Impact mapper for connecting failures to downstream assets and owners.
"""

import logging
from typing import Any, Dict, List, Set

from collibra_client.catalog.connections import DatabaseConnection
from collibra_client.core.exceptions import CollibraAPIError

logger = logging.getLogger(__name__)

class ImpactMapper:
    """
    Handles mapping from failed Edge connections to impacted Catalog Database assets and owners.
    """

    def __init__(self, client, db_manager):
        self.client = client
        self.db_manager = db_manager

    def get_impacted_assets_and_owners(self, edge_connection_id: str) -> List[Dict[str, Any]]:
        """
        Identify all Catalog Database assets and their owners impacted by an Edge connection failure.
        
        Args:
            edge_connection_id: The ID of the failed Edge connection.
            
        Returns:
            List of dictionaries containing database_id, connection_name, and owner information.
        """
        impacted = []
        try:
            # 1. Find all Catalog Database connections linked to this Edge connection ID
            catalog_conns = self.db_manager.list_database_connections(edge_connection_id=edge_connection_id)
            if not catalog_conns:
                logger.debug("  No Catalog Database connection found for failed Edge connection %s", edge_connection_id)
                return []

            for conn in catalog_conns:
                if not conn.database_id:
                    logger.debug("  Catalog connection %s has no linked Database asset", conn.name)
                    continue
                
                # 2. Retrieve owner information for the specific database asset
                owners_info = self.get_database_owners(conn.database_id)
                
                impacted.append({
                    "connection": conn,
                    "owners": owners_info
                })
                
        except Exception as e:
            logger.warning("  Failed to map impacts for Edge connection %s: %s", edge_connection_id, e)
            
        return impacted

    def get_database_owners(self, database_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve and deduplicate owners for a specific database asset.
        """
        try:
            db_asset = self.db_manager.get_database_asset(database_id)
            owner_ids = db_asset.get("ownerIds") or db_asset.get("ownerId")
            if not owner_ids:
                return []
            
            if not isinstance(owner_ids, list):
                owner_ids = [owner_ids]
                
            seen_ids: Set[str] = set()
            unique_owners = []
            
            for oid in owner_ids:
                if not oid or oid in seen_ids:
                    continue
                
                seen_ids.add(oid)
                owner_info = self._fetch_user_details(oid)
                unique_owners.append(owner_info)
                
            return unique_owners
        except Exception as e:
            logger.debug("  Error retrieving owners for database %s: %s", database_id, e)
            return []

    def _fetch_user_details(self, user_id: str) -> Dict[str, Any]:
        """Fetch user details from Collibra REST API."""
        try:
            user = self.client.get_user(user_id)
            return {
                "owner_id": user_id,
                "name": user.get("fullName") or (
                    f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()
                ) or user.get("username"),
                "email": user.get("email") or user.get("emailAddress"),
                "username": user.get("username"),
            }
        except Exception:
            # Fallback to just returning the ID if profile lookup fails
            return {"owner_id": user_id, "name": None, "email": None, "username": None}
