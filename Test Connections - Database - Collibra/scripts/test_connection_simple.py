"""
Simple connection test script.

This script tests the OAuth connection to Collibra without requiring
database connection testing. Useful for quick validation.
"""

import logging
import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from collibra_client.logging_utils import setup_script_logging
    setup_script_logging(
        log_format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if os.environ.get("COLLIBRA_LOG_FILE"):
        h = logging.FileHandler(os.environ["COLLIBRA_LOG_FILE"], encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        logging.getLogger().addHandler(h)
logger = logging.getLogger(__name__)

try:
    from collibra_client import CollibraClient, CollibraConfig
except ImportError as e:
    logger.error("Error importing collibra_client: %s", e)
    logger.info(
        "Make sure dependencies are installed: pip install requests python-dotenv or uv sync"
    )
    sys.exit(1)


def test_oauth_connection():
    """Test OAuth connection to Collibra."""
    logger.info("=" * 60)
    logger.info("COLLIBRA OAUTH CONNECTION TEST")
    logger.info("=" * 60)

    try:
        logger.info("Loading configuration from environment variables...")
        config = CollibraConfig.from_env()
        logger.info("Base URL: %s", config.base_url)
        logger.info(
            "Client ID: %s",
            f"{config.client_id[:10]}..." if config.client_id else "Not set",
        )

        logger.info("Creating Collibra client...")
        client = CollibraClient(
            base_url=config.base_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
            timeout=config.timeout,
        )
        logger.info("Client created")

        logger.info("Testing OAuth connection...")
        if client.test_connection():
            logger.info("Connection successful")

            logger.info("Fetching current user information...")
            try:
                current_user = client.get("/rest/2.0/users/current")
                username = (
                    current_user.get("username")
                    or current_user.get("name")
                    or current_user.get("fullName")
                    or current_user.get("emailAddress")
                    or "Unknown"
                )
                user_id = current_user.get("id", "N/A")
                email = current_user.get("emailAddress", "N/A")
                logger.info("Current user: %s", username)
                logger.info("User ID: %s", user_id)
                if email != "N/A":
                    logger.info("Email: %s", email)
                if username == "Unknown":
                    logger.warning(
                        "Username not found. Available fields: %s",
                        list(current_user.keys())[:5],
                    )
            except Exception as e:
                logger.warning("Could not fetch user info: %s", e)

            logger.info("=" * 60)
            logger.info("ALL TESTS PASSED")
            logger.info("=" * 60)
            return True
        else:
            logger.error("Connection failed")
            return False

    except ValueError as e:
        logger.error("Configuration error: %s", e)
        logger.info(
            "Ensure COLLIBRA_BASE_URL, COLLIBRA_CLIENT_ID, COLLIBRA_CLIENT_SECRET are set, or use .env."
        )
        return False

    except Exception as e:
        logger.exception("Error: %s", e)
        return False


if __name__ == "__main__":
    success = test_oauth_connection()
    sys.exit(0 if success else 1)

