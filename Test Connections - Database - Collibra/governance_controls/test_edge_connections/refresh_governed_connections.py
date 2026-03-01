"""
Test database connections for a governed set of edge_connection_ids.

Usage:
    # Using CLI arguments (recommended)
    python refresh_governed_connections.py --edge-site-id <id1> --edge-site-id <id2>

    # Using YAML config file
    python refresh_governed_connections.py --yaml-config governed_connections.yaml

    # Using default YAML file (backward compatible)
    python refresh_governed_connections.py

The script calls the Catalog refresh API for each edge_connection_id, waits for each
refresh job to complete, then notifies owners of failed connections and prints a summary report.
"""

import argparse
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging (colored console when TTY + optional file)
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
        CollibraAPIError,
        CollibraClient,
        CollibraConfig,
        DatabaseConnectionManager,
    )
    from governance_controls.test_edge_connections.connection_monitor import ConnectionMonitor
    from governance_controls.test_edge_connections.governed_config import load_governed_config
    from governance_controls.test_edge_connections.notifications import ConsoleNotificationHandler
except ImportError as e:
    logger.error("Error importing collibra_client: %s", e)
    logger.info("Make sure dependencies are installed: pip install requests python-dotenv pyyaml")
    sys.exit(1)


from governance_controls.test_edge_connections.logic.orchestrator import GovernanceOrchestrator
from governance_controls.test_edge_connections.governed_config import load_governed_config
from governance_controls.test_edge_connections.notifications.handlers import ConsoleNotificationHandler


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Test Collibra Edge database connections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test specific Edge Sites by ID
  %(prog)s --edge-site-id 7d343ace-eecf-4c8c-af2c-3420280e6a2d

  # Test multiple Edge Sites
  %(prog)s --edge-site-id <id1> --edge-site-id <id2> --edge-site-id <id3>

  # Use custom YAML config file
  %(prog)s --yaml-config /path/to/config.yaml

  # Use default YAML config (backward compatible)
  %(prog)s
        """
    )

    parser.add_argument(
        "--edge-site-id",
        action="append",
        dest="edge_site_ids",
        metavar="ID",
        help="Edge Site ID to test (can be specified multiple times)"
    )

    parser.add_argument(
        "--yaml-config",
        type=str,
        metavar="PATH",
        help="Path to YAML configuration file (default: governed_connections.yaml)"
    )

    parser.add_argument(
        "--max-workers",
        type=int,
        default=3,
        help="Maximum parallel workers for connection testing (default: 3)"
    )

    parser.add_argument(
        "--poll-delay",
        type=int,
        default=5,
        help="Seconds between job status polls (default: 5)"
    )

    parser.add_argument(
        "--job-timeout",
        type=int,
        default=60,
        help="Maximum seconds to wait for job completion (default: 60)"
    )

    return parser.parse_args()


def main():
    try:
        # Parse CLI arguments
        args = parse_arguments()

        logger.info("Loading configuration...")
        config = CollibraConfig.from_env()

        # Create client with flexible authentication
        client = CollibraClient(
            base_url=config.base_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
            username=config.username,
            password=config.password,
            timeout=config.timeout,
        )

        if not client.test_connection():
            logger.error("Connection failed - check your credentials")
            return 1

        db_manager = DatabaseConnectionManager(client=client, use_oauth=True)

        # Determine governed scope: CLI args take precedence over YAML
        if args.edge_site_ids:
            # Use Edge Site IDs from CLI arguments
            logger.info("Using Edge Site IDs from command-line arguments")
            governed_edge_ids = args.edge_site_ids
            # Create simple metadata for CLI-provided IDs
            metadata = {
                edge_id: {
                    "name": f"Edge Site {edge_id[:8]}...",
                    "description": "Provided via CLI",
                    "environment": "unknown",
                    "owner_team": "unknown"
                }
                for edge_id in governed_edge_ids
            }
        else:
            # Load from YAML config file
            yaml_path = args.yaml_config if args.yaml_config else None
            logger.info("Loading governed scope from YAML configuration...")

            try:
                governed_edge_ids, metadata = load_governed_config(yaml_path)
            except FileNotFoundError as e:
                logger.error(str(e))
                logger.info("TIP: Provide Edge Site IDs via --edge-site-id argument")
                return 1

            if not governed_edge_ids:
                logger.error("No governed edge connection IDs found in YAML config.")
                logger.info("TIP: Provide Edge Site IDs via --edge-site-id argument")
                return 1

        logger.info("Testing %d Edge Site(s)", len(governed_edge_ids))

        # Instantiate Orchestrator
        orchestrator = GovernanceOrchestrator(
            client=client,
            db_manager=db_manager,
            notification_handler=ConsoleNotificationHandler(),
            max_workers=args.max_workers,
            poll_delay=args.poll_delay,
            job_timeout=args.job_timeout
        )

        # Run workflow
        orchestrator.run(governed_edge_ids, metadata)

        return 0

    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        return 130
    except Exception as e:
        logger.exception("Execution failed: %s", e)
        return 1

if __name__ == "__main__":
    sys.exit(main())
