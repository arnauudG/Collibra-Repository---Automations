#!/usr/bin/env python3
"""
CLI utility to list all database connections for a given Edge Site ID.
"""

import argparse
import sys
import logging
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from collibra_client import CollibraClient, CollibraConfig
from collibra_client.catalog.connections import DatabaseConnectionManager
from collibra_client.logging_utils import setup_script_logging

def main():
    parser = argparse.ArgumentParser(description="List connections for an Edge Site.")
    parser.add_argument("site_id", help="The UUID of the Edge Site")
    args = parser.parse_args()

    setup_script_logging()
    logger = logging.getLogger(__name__)

    try:
        config = CollibraConfig.from_env()
        client = CollibraClient(
            base_url=config.base_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
        )
        db_manager = DatabaseConnectionManager(client)

        logger.info("Fetching connections for Edge Site: %s ...", args.site_id)
        connections = db_manager.get_edge_site_connections(args.site_id)

        if not connections:
            logger.warning("No connections found for this Site ID.")
            return 0

        print("\n" + "=" * 120)
        print(f"{'CONNECTION NAME':<40} | {'FAMILY':<15} | {'TYPE ID':<15} | {'CONNECTION ID':<36}")
        print("-" * 120)
        for conn in connections:
            # For brevity in the script, we'll fetch details for each to see the family/type
            detail = db_manager.get_connection_detail(conn['id'])
            name = detail.get('name', 'N/A')
            family = detail.get('family', 'N/A')
            type_id = detail.get('connectionTypeId', 'N/A')
            cid = detail.get('id', 'N/A')
            print(f"{name:<40} | {family:<15} | {type_id:<15} | {cid:<36}")
        print("=" * 120 + "\n")

    except Exception as e:
        logger.error("Error: %s", e)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
