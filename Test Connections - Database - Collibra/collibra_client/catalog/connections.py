"""
Database connection management module for Collibra Catalog Database Registration API.

This module provides functionality to manage and test database connections
in Collibra, including listing connections, refreshing connections, and
notifying owners of connection failures.
"""

import base64
import json
from dataclasses import dataclass
from typing import Any, Optional

import requests
from collibra_client.core.client import CollibraClient
from collibra_client.core.exceptions import CollibraAPIError


@dataclass
class DatabaseConnection:
    """
    Represents a database connection in Collibra.

    Attributes:
        id: The unique identifier (UUID) of the database connection.
        name: The exact name of the database (catalog) read from the source.
        edge_connection_id: The ID of the Edge connection.
        database_id: Optional ID of the Database asset linked with this connection.
    """

    id: str
    name: str
    edge_connection_id: str
    database_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DatabaseConnection":
        """
        Create a DatabaseConnection instance from API response data.

        Args:
            data: Dictionary containing database connection data from API.

        Returns:
            DatabaseConnection instance.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            edge_connection_id=data["edgeConnectionId"],
            database_id=data.get("databaseId"),
        )


class DatabaseConnectionManager:
    """
    Manager for Collibra database connections.

    This class provides methods to interact with Collibra's Catalog Database
    Registration API to list, refresh, and test database connections.

    The Catalog Database Registration API can use either:
    - OAuth Bearer token (recommended, uses the client's OAuth token)
    - Basic Authentication (username/password, if provided)

    Attributes:
        client: CollibraClient instance for making API requests.
        use_oauth: Whether to use OAuth Bearer token (default: True).
        username: Optional username for Basic Authentication (if not using OAuth).
        password: Optional password for Basic Authentication (if not using OAuth).
    """

    CATALOG_API_BASE = "/rest/catalogDatabase/v1"

    def __init__(
        self,
        client: CollibraClient,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_oauth: bool = True,
    ):
        """
        Initialize the database connection manager.

        Args:
            client: CollibraClient instance configured with base URL.
            username: Optional username for Basic Authentication (if use_oauth=False).
            password: Optional password for Basic Authentication (if use_oauth=False).
            use_oauth: Whether to use OAuth Bearer token (default: True).
                      If True, uses the client's OAuth token instead of Basic Auth.
        """
        self.client = client
        self.use_oauth = use_oauth
        self.username = username
        self.password = password

    def _get_auth_header(self) -> str:
        """
        Get authentication header value.

        Uses OAuth Bearer token if use_oauth=True, otherwise Basic Auth.

        Returns:
            Authorization header value (either "Bearer <token>" or "Basic <encoded>").
        """
        if self.use_oauth:
            # Use OAuth Bearer token from the client
            token = self.client._authenticator.get_access_token()
            return f"Bearer {token}"
        else:
            # Use Basic Authentication
            if not self.username or not self.password:
                raise ValueError(
                    "Basic Auth credentials required when use_oauth=False. "
                    "Provide username and password, or set use_oauth=True."
                )
            credentials = f"{self.username}:{self.password}"
            encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
            return f"Basic {encoded}"

    def _make_basic_auth_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Make an authenticated request to the Catalog Database API.

        Uses OAuth Bearer token if use_oauth=True, otherwise Basic Authentication.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path.
            params: Optional query parameters.
            json_data: Optional JSON body data.

        Returns:
            JSON response as dictionary.

        Raises:
            CollibraAPIError: If the request fails.
        """
        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"{self.client.base_url}{endpoint}"
        request_kwargs: dict[str, Any] = {
            "headers": headers,
            "timeout": self.client.timeout,
        }

        if params:
            request_kwargs["params"] = params

        if json_data:
            request_kwargs["json"] = json_data

        try:
            response = self.client._session.request(method, url, **request_kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            response_body = None
            error_message = str(e)

            if e.response:
                try:
                    response_body = e.response.json()
                    error_message = response_body.get("message", response_body.get("error", str(e)))
                except (ValueError, json.JSONDecodeError):
                    response_body = e.response.text
                    error_message = response_body or str(e)

            raise CollibraAPIError(
                f"Database API request failed: {error_message}",
                status_code=status_code,
                response_body=response_body,
            ) from e
        except requests.exceptions.RequestException as e:
            raise CollibraAPIError(f"Network error during database API request: {e}") from e

    def list_database_connections(
        self,
        edge_connection_id: Optional[str] = None,
        schema_connection_id: Optional[str] = None,
        limit: int = 0,
        offset: int = 0,
    ) -> list[DatabaseConnection]:
        """
        List all available database connections.

        This method retrieves a list of database connections that have been
        registered with the catalog. Only connections known to the catalog are returned.

        **Important**: To ensure you get up-to-date database connections, call
        `refresh_database_connections(edge_connection_id=...)` for each governed
        edge before calling this method.

        Args:
            edge_connection_id: Optional UUID of the Edge connection to filter by.
            schema_connection_id: Optional UUID of the schema connection to filter by.
            limit: Maximum number of results to retrieve (max 500, default 0 = all).
            offset: Index of the first result to retrieve (for pagination).

        Returns:
            List of DatabaseConnection objects.

        Raises:
            CollibraAPIError: If the API request fails.

        Examples:
            >>> manager = DatabaseConnectionManager(client, use_oauth=True)
            >>> # Refresh a governed edge first
            >>> manager.refresh_database_connections(edge_connection_id="edge-uuid")
            >>> # Then list connections (optionally filter by edge_connection_id)
            >>> connections = manager.list_database_connections(limit=100)
            >>> for conn in connections:
            ...     print(f"Connection: {conn.name} (ID: {conn.id})")
        """
        endpoint = f"{self.CATALOG_API_BASE}/databaseConnections"

        params = {}
        if edge_connection_id:
            params["edgeConnectionId"] = edge_connection_id
        if schema_connection_id:
            params["schemaConnectionId"] = schema_connection_id
        if limit > 0:
            params["limit"] = str(min(limit, 500))  # Enforce max limit
        if offset > 0:
            params["offset"] = str(offset)

        response = self._make_basic_auth_request("GET", endpoint, params=params)
        results = response.get("results", [])

        return [DatabaseConnection.from_dict(conn_data) for conn_data in results]

    def refresh_database_connections(self, edge_connection_id: str) -> dict[str, Any]:
        """
        Refresh database connections in the catalog for a specific Edge connection.

        This method triggers a refresh of database connections available in
        the catalog with the data source (required by the API). Use a governed
        set of edge_connection_ids from your YAML config.

        Args:
            edge_connection_id: UUID of the Edge connection to refresh (required).

        Returns:
            API response dictionary (202 with Job body including id for polling).

        Raises:
            ValueError: If edge_connection_id is missing or empty.
            CollibraAPIError: If the refresh operation fails.

        Examples:
            >>> result = manager.refresh_database_connections(
            ...     edge_connection_id="edge-uuid"
            ... )
            >>> job_id = result.get("id")
        """
        if not edge_connection_id or not edge_connection_id.strip():
            raise ValueError("edge_connection_id is required for refresh")
        endpoint = f"{self.CATALOG_API_BASE}/databaseConnections/refresh"
        params = {"edgeConnectionId": edge_connection_id}
        return self._make_basic_auth_request("POST", endpoint, params=params)

    def test_edge_connection(self, edge_connection_id: str) -> str:
        """
        Explicitly run a connection test on an Edge connection via GraphQL.

        This uses the Edge API's native capability to explicitly verify the connection.

        Args:
            edge_connection_id: UUID of the Edge connection to test (required).

        Returns:
            The job ID string for tracking the connection test progress.

        Raises:
            CollibraAPIError: If the GraphQL request fails.

        Examples:
            >>> job_id = manager.test_edge_connection(
            ...     edge_connection_id="edge-uuid"
            ... )
        """
        query = """
        mutation TestConnection($id: ID!) {
          job: connectionTestConnection(id: $id) {
            jobId
          }
        }
        """
        variables = {"id": edge_connection_id}

        response = self.client.post_graphql(
            endpoint="/edge/api/graphql",
            query=query,
            variables=variables,
            operation_name="TestConnection",
        )

        try:
            return response["data"]["job"]["jobId"]
        except KeyError as e:
            raise CollibraAPIError(
                f"Unexpected structure in GraphQL response when getting jobId: {response}"
            ) from e

    def get_edge_site_connections(
        self, edge_site_id: str, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        Fetch all child database connections nested under an Edge Site via GraphQL.

        Args:
            edge_site_id: UUID of the parent Edge Site.
            limit: Pagination limit, max 50 default.
            offset: Pagination offset, default 0.

        Returns:
            A list of connection dictionaries containing 'id', 'name', and 'description'.

        Raises:
            CollibraAPIError: If the GraphQL request fails.
        """
        query = """
        query Connections($edgeSiteId: ID!, $offset: Int!, $limit: Int!, $filter: ConnectionFindFilterInput) {
          edgeSiteConnections: edgeSiteById(id: $edgeSiteId) {
            id
            connections(input: {offset: $offset, limit: $limit, filter: $filter}) {
              limit
              offset
              total
              edges {
                node {
                  ...ConnectionResult
                }
              }
            }
          }
        }

        fragment ConnectionResult on Connection {
          id
          name
          description
        }
        """
        variables = {"edgeSiteId": edge_site_id, "limit": limit, "offset": offset, "filter": {}}

        response = self.client.post_graphql(
            endpoint="/edge/api/graphql",
            query=query,
            variables=variables,
            operation_name="Connections",
        )

        try:
            site_data = response.get("data", {}).get("edgeSiteConnections")
            if not site_data:
                return []
            edges = site_data.get("connections", {}).get("edges", [])
            return [edge.get("node", {}) for edge in edges if edge.get("node")]
        except Exception as e:
            raise CollibraAPIError(
                f"Failed to parse Edge Site connections from GraphQL: {response}"
            ) from e

    def get_connection_detail(self, connection_id: str) -> dict[str, Any]:
        """
        Fetch detailed metadata for a specific connection using GraphQL.

        This includes parameters (driver, connection string), vaultId,
        and family type information.

        Args:
            connection_id: UUID of the connection.

        Returns:
            Dictionary containing detailed connection metadata.

        Raises:
            CollibraAPIError: If the GraphQL request fails.
        """
        query = """
        query ConnectionDetail($connectionId: ID!) {
          connectionById(id: $connectionId) {
            id
            name
            description
            vaultId
            parameters
            connectionTypeId
            family
          }
        }
        """
        variables = {"connectionId": connection_id}

        response = self.client.post_graphql(
            endpoint="/edge/api/graphql",
            query=query,
            variables=variables,
            operation_name="ConnectionDetail",
        )

        try:
            return response.get("data", {}).get("connectionById") or {}
        except Exception as e:
            raise CollibraAPIError(
                f"Failed to parse Connection Details from GraphQL: {response}"
            ) from e

    def get_database_connection_by_id(self, connection_id: str) -> Optional[DatabaseConnection]:
        """
        Get a specific database connection by ID.

        Args:
            connection_id: UUID of the database connection.

        Returns:
            DatabaseConnection if found, None otherwise.

        Raises:
            CollibraAPIError: If the API request fails (except 404).
        """
        endpoint = f"{self.CATALOG_API_BASE}/databaseConnections/{connection_id}"
        try:
            response = self._make_basic_auth_request("GET", endpoint)
            return DatabaseConnection.from_dict(response)
        except CollibraAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def synchronize_database_metadata(self, database_id: str) -> dict[str, Any]:
        """
        Trigger a metadata sync job for a database asset (Catalog API).

        This method calls the Catalog API endpoint to start a metadata
        synchronization job. This project governs connections via refresh only;
        use this method only if you need metadata sync separately.

        Args:
            database_id: UUID of the Database asset.

        Returns:
            Dictionary containing job information (e.g. jobId, status).

        Raises:
            CollibraAPIError: If the request fails.

        Examples:
            >>> result = manager.synchronize_database_metadata("database-uuid")
            >>> job_id = result.get("jobId")
            >>> status = client.get_job_status(job_id)
        """
        endpoint = f"{self.CATALOG_API_BASE}/databases/{database_id}/synchronizeMetadata"
        return self._make_basic_auth_request("POST", endpoint)

    def get_database_asset(self, database_id: str) -> dict[str, Any]:
        """
        Get database asset details by ID.

        This method retrieves detailed information about a database asset,
        including owner information, metadata, and configuration.

        Args:
            database_id: UUID of the Database asset.

        Returns:
            Dictionary containing database asset information, including:
            - id: Database asset ID
            - name: Database name
            - ownerIds: Array of owner user IDs (from Catalog Database API)
            - ownerId: Owner user ID (fallback, if available)
            - Other asset properties

        Raises:
            CollibraAPIError: If the API request fails.

        Examples:
            >>> db_asset = manager.get_database_asset("database-uuid")
            >>> owner_id = db_asset.get("ownerId")
            >>> if owner_id:
            ...     user = client.get(f"/rest/2.0/users/{owner_id}")
            ...     print(f"Owner email: {user.get('email')}")
        """
        endpoint = f"{self.CATALOG_API_BASE}/databases/{database_id}"
        return self._make_basic_auth_request("GET", endpoint)
