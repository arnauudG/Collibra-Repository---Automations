"""
Simple script to list database connections for governed edge_connection_ids.

Loads governed_connections.yaml; refreshes only those edge connections,
then lists database connections and filters to the governed set (and those
with a database asset ID). With no YAML or empty YAML, skips refresh and
lists all connections with database_id.
"""

import logging
import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
try:
    from collibra_client.logging_utils import setup_script_logging
    setup_script_logging(log_format=_LOG_FORMAT, datefmt=_LOG_DATEFMT)
except ImportError:
    logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT, datefmt=_LOG_DATEFMT)
    if os.getenv("COLLIBRA_LOG_FILE"):
        _fh = logging.FileHandler(os.getenv("COLLIBRA_LOG_FILE"), encoding="utf-8")
        _fh.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT))
        logging.getLogger().addHandler(_fh)
logger = logging.getLogger(__name__)

try:
    from collibra_client import (
        CollibraClient,
        CollibraConfig,
        DatabaseConnectionManager,
        load_governed_config,
    )
except ImportError as e:
    logger.error("Error importing collibra_client: %s", e)
    logger.info("Make sure dependencies are installed: pip install requests python-dotenv pyyaml")
    sys.exit(1)


def test_list_database_connections():
    """Test listing database connections."""
    logger.info("=" * 60)
    logger.info("DATABASE CONNECTION ID FETCHING TEST")
    logger.info("=" * 60)

    try:
        logger.info("Loading configuration from environment variables...")
        config = CollibraConfig.from_env()
        logger.info("Base URL: %s", config.base_url)
        logger.info(
            "Client ID: %s...",
            config.client_id[:20] if config.client_id else "Not set",
        )

        logger.info("Creating Collibra OAuth client...")
        client = CollibraClient(
            base_url=config.base_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
            timeout=config.timeout,
        )
        logger.info("OAuth client created")

        logger.info("Testing OAuth connection...")
        if not client.test_connection():
            logger.error("OAuth connection failed")
            return False
        logger.info("OAuth connection successful")

        logger.info("Creating database connection manager (OAuth Bearer token)...")
        db_manager = DatabaseConnectionManager(client=client, use_oauth=True)
        logger.info("Database manager created")

        governed_edge_ids = set()
        try:
            governed_edge_ids, _ = load_governed_config()
            if governed_edge_ids:
                logger.info("Refreshing %d governed edge connection(s)...", len(governed_edge_ids))
                refreshed_count = 0
                for edge_id in governed_edge_ids:
                    try:
                        db_manager.refresh_database_connections(edge_connection_id=edge_id)
                        refreshed_count += 1
                    except Exception as e:
                        logger.warning(
                            "Could not refresh edge connection %s...: %s",
                            edge_id[:8],
                            e,
                        )
                logger.info(
                    "Refreshed %d/%d edge connection(s)",
                    refreshed_count,
                    len(governed_edge_ids),
                )
            else:
                logger.info("No governed edge connection IDs in YAML (or file empty). Skipping refresh.")
        except FileNotFoundError:
            logger.info("Governed connections YAML not found. Skipping refresh; listing existing connections.")
        except ValueError as e:
            logger.warning("Could not load governed config: %s. Skipping refresh.", e)

        logger.info("Fetching database connections...")
        try:
            all_connections = db_manager.list_database_connections()

            # Filter: must have database_id; if we have governed set, also filter by edge_connection_id
            if governed_edge_ids:
                connections = [
                    conn
                    for conn in all_connections
                    if conn.database_id is not None
                    and conn.edge_connection_id in governed_edge_ids
                ]
            else:
                connections = [conn for conn in all_connections if conn.database_id is not None]

            logger.info(
                "Successfully fetched %d total database connection(s), filtered to %d (database asset ID%s)",
                len(all_connections),
                len(connections),
                " governed set" if governed_edge_ids else "",
            )

            if len(connections) == 0:
                logger.warning(
                    "No database connections found with both edge connection ID and database asset ID."
                )
                logger.info(
                    "Possible causes: no connections linked to Database assets yet, or need to be linked/refreshed in Collibra."
                )
            else:
                logger.info("Database connections (edge ID + database asset ID):")
                for i, conn in enumerate(connections, 1):
                    logger.info(
                        "  %d. %s | ID: %s | Edge: %s | DB: %s",
                        i,
                        conn.name,
                        conn.id,
                        conn.edge_connection_id,
                        conn.database_id,
                    )
                logger.info(
                    "Summary: total fetched %d, with asset ID %d",
                    len(all_connections),
                    len(connections),
                )

            logger.info("=" * 60)
            logger.info("TEST COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            return True

        except Exception as e:
            error_msg = str(e)
            logger.error("Error fetching database connections: %s", error_msg)
            if "401" in error_msg or "Unauthorized" in error_msg:
                logger.warning(
                    "Authentication failed (401). Check COLLIBRA_BASIC_AUTH_* credentials."
                )
            elif "403" in error_msg or "Forbidden" in error_msg:
                logger.warning(
                    "Access denied (403). Credentials valid but insufficient permission."
                )
            else:
                logger.exception("Unexpected error")
            return False

    except ValueError as e:
        logger.error("Configuration error: %s", e)
        logger.info(
            "Ensure COLLIBRA_BASE_URL, COLLIBRA_CLIENT_ID, COLLIBRA_CLIENT_SECRET, "
            "COLLIBRA_BASIC_AUTH_USERNAME, COLLIBRA_BASIC_AUTH_PASSWORD are set."
        )
        return False

    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        return False


if __name__ == "__main__":
    success = test_list_database_connections()
    sys.exit(0 if success else 1)

