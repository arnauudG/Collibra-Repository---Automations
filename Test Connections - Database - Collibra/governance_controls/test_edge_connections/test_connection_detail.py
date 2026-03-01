#!/usr/bin/env python3
"""
Debug utility to fetch and display detailed metadata for a specific Edge connection.

Usage:
    uv run python governance_controls/test_edge_connections/test_connection_detail.py <CONNECTION_ID>

Returns the full connection metadata from the Edge GraphQL API, including:
  - name, family, connectionTypeId
  - parameters (driver, connection string, etc.)
  - vaultId

Useful for verifying the heuristic filtering logic and inspecting connection configuration.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch detailed metadata for a specific Edge connection."
    )
    parser.add_argument("connection_id", help="The UUID of the connection to inspect")
    args = parser.parse_args()

    from collibra_client import CollibraClient, CollibraConfig, DatabaseConnectionManager

    config = CollibraConfig.from_env()
    client = CollibraClient(
        base_url=config.base_url,
        client_id=config.client_id,
        client_secret=config.client_secret,
    )
    db_manager = DatabaseConnectionManager(client)

    connection_id = args.connection_id
    logger.info("Fetching details for connection: %s", connection_id)

    try:
        details = db_manager.get_connection_detail(connection_id)
        print("\nConnection Metadata:")
        print(json.dumps(details, indent=2))

        if details.get("id") == connection_id:
            logger.info("Connection detail retrieved successfully.")
        else:
            logger.warning("ID mismatch or empty response.")

    except Exception as e:
        logger.error("Failed to fetch connection details: %s", e)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
