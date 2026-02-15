"""
Test database connections for a governed set of edge_connection_ids.

Loads governed_connections.yaml, calls the Catalog refresh API for each
edge_connection_id, waits for each refresh job to complete, then notifies
owners of failed connections and prints a summary report. Governs connections only (no metadata sync).
"""

import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
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
        CollibraClient,
        CollibraConfig,
        ConsoleNotificationHandler,
        DatabaseConnectionManager,
        load_governed_config,
    )
except ImportError as e:
    logger.error("Error importing collibra_client: %s", e)
    logger.info("Make sure dependencies are installed: pip install requests python-dotenv pyyaml")
    sys.exit(1)


def get_database_owners_info(client, db_manager, database_id):
    """Return list of owner dicts (owner_id, name, email, username) for a database asset.
    Deduplicated by owner_id so the same person (e.g. Owner + Steward) is only listed once.
    """
    try:
        db_asset = db_manager.get_database_asset(database_id)
        owner_ids = db_asset.get("ownerIds") or db_asset.get("ownerId")
        if not owner_ids:
            return []
        if not isinstance(owner_ids, list):
            owner_ids = [owner_ids]
        # Deduplicate by owner_id (same person can appear multiple times in ownerIds)
        seen_ids = set()
        unique_owner_ids = []
        for oid in owner_ids:
            if oid and oid not in seen_ids:
                seen_ids.add(oid)
                unique_owner_ids.append(oid)
        owners = []
        for owner_id in unique_owner_ids:
            try:
                user = client.get_user(owner_id)
                owners.append({
                    "owner_id": owner_id,
                    "name": user.get("fullName") or (
                        f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()
                    ) or user.get("username"),
                    "email": user.get("email") or user.get("emailAddress"),
                    "username": user.get("username"),
                })
            except Exception:
                owners.append({"owner_id": owner_id, "name": None, "email": None, "username": None})
        return owners
    except Exception:
        return []


def monitor_job_status(client, job_id, max_attempts=24, delay_seconds=5):
    """Poll job status until terminal state (COMPLETED, ERROR, etc.)."""
    for attempt in range(max_attempts):
        try:
            job_status = client.get_job_status(job_id)
            status = (
                job_status.get("status")
                or job_status.get("state")
                or job_status.get("jobStatus")
                or job_status.get("currentStatus")
                or "UNKNOWN"
            )
            status_upper = str(status).upper()
            message_raw = (
                job_status.get("message")
                or job_status.get("statusMessage")
                or ""
            )

            if status_upper in ["COMPLETED", "SUCCESS", "DONE", "FINISHED"]:
                return {"status": "completed", "message": message_raw}
            if status_upper in ["FAILED", "ERROR", "CANCELLED", "CANCELED"]:
                error_msg = (
                    job_status.get("error")
                    or job_status.get("errorMessage")
                    or message_raw
                    or "Unknown error"
                )
                return {"status": "failed", "message": error_msg, "error": error_msg}

            if attempt < max_attempts - 1:
                time.sleep(delay_seconds)
        except Exception as e:
            if attempt < max_attempts - 1:
                time.sleep(delay_seconds)
            else:
                return {"status": "error", "message": str(e)}
    return {
        "status": "timeout",
        "message": f"Job did not complete within {max_attempts * delay_seconds} seconds",
    }


def main():
    logger.info("=" * 60)
    logger.info("CONNECTION TEST – Refresh governed edge connections")
    logger.info("=" * 60)

    try:
        logger.info("Loading configuration...")
        config = CollibraConfig.from_env()
        client = CollibraClient(
            base_url=config.base_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
            timeout=config.timeout,
        )
        if not client.test_connection():
            logger.error("OAuth connection failed")
            return 1
        logger.info("OAuth connection successful")

        db_manager = DatabaseConnectionManager(client=client, use_oauth=True)
        logger.info("Database manager created")

        logger.info("Loading governed connections from YAML...")
        try:
            governed_edge_ids, metadata = load_governed_config()
        except FileNotFoundError as e:
            logger.error("%s", e)
            return 1
        except ValueError as e:
            logger.error("%s", e)
            return 1

        if not governed_edge_ids:
            logger.error("No governed edge connection IDs in YAML (or file is empty).")
            return 1
        logger.info("Found %d governed edge connection(s)", len(governed_edge_ids))

        succeeded = []
        failed = []

        for i, edge_id in enumerate(sorted(governed_edge_ids), 1):
            name = (metadata.get(edge_id) or {}).get("name", edge_id[:8] + "...")
            logger.info("[%d/%d] Testing: %s (%s...)", i, len(governed_edge_ids), name, edge_id[:8])

            try:
                response = db_manager.refresh_database_connections(
                    edge_connection_id=edge_id
                )
            except Exception as e:
                logger.warning("Refresh request failed: %s", e)
                failed.append((edge_id, name, str(e)))
                continue

            job_id = response.get("id")
            if not job_id:
                logger.warning("No job ID in response (cannot wait for completion)")
                failed.append((edge_id, name, "No job ID in 202 response"))
                continue

            logger.info("Job ID: %s – waiting for completion...", job_id)
            result = monitor_job_status(client, job_id, max_attempts=24, delay_seconds=5)

            if result["status"] == "completed":
                logger.info("Completed")
                succeeded.append((edge_id, name))
            else:
                msg = result.get("error") or result.get("message", "Unknown error")
                logger.warning("%s: %s", result["status"], msg)
                failed.append((edge_id, name, msg))

        # Notify owners of failed connections and build report
        notification_handler = ConsoleNotificationHandler()
        notifications_sent = []
        failed_connections_detail = []

        for edge_id, edge_name, error_msg in failed:
            try:
                conns = db_manager.list_database_connections(edge_connection_id=edge_id)
            except Exception:
                conns = []
            for conn in conns:
                if not conn.database_id:
                    continue
                owners_info = get_database_owners_info(client, db_manager, conn.database_id)
                failed_connections_detail.append({
                    "connection_name": conn.name,
                    "connection_id": conn.id,
                    "database_id": conn.database_id,
                    "edge_name": edge_name,
                    "edge_id": edge_id,
                    "error": error_msg,
                    "owners": owners_info,
                })
                for owner in owners_info:
                    owner_info = {
                        "id": owner.get("owner_id"),
                        "username": owner.get("username"),
                        "email": owner.get("email"),
                        "fullName": owner.get("name"),
                    }
                    notification_handler.notify(conn, error_msg, owner_info)
                    notifications_sent.append({
                        "connection": conn.name,
                        "database_id": conn.database_id,
                        "owner_id": owner.get("owner_id"),
                        "owner": owner.get("email") or owner.get("username") or owner.get("owner_id"),
                    })

        # Summary report
        logger.info("")
        logger.info("=" * 60)
        logger.info("SUMMARY REPORT")
        logger.info("=" * 60)
        logger.info("  Succeeded: %d", len(succeeded))
        logger.info("  Failed:    %d", len(failed))
        if failed:
            logger.info("Failed edge connections:")
            for edge_id, name, err in failed:
                logger.info("  - %s (%s...): %s", name, edge_id[:8], err)

        if failed_connections_detail:
            logger.info("")
            logger.info("=" * 60)
            logger.info("FAILED DATABASES AND THEIR OWNERS")
            logger.info("=" * 60)
            for item in failed_connections_detail:
                logger.info("Connection: %s", item["connection_name"])
                logger.info("  Database ID: %s", item["database_id"])
                logger.info("  Edge: %s (%s...)", item["edge_name"], item["edge_id"][:8])
                logger.info("  Error: %s", item["error"])
                if item["owners"]:
                    logger.info("  Owner(s):")
                    for o in item["owners"]:
                        logger.info(
                            "    - %s (%s) [user id: %s]",
                            o.get("name") or o.get("username") or o.get("owner_id"),
                            o.get("email") or "no email",
                            o.get("owner_id") or "N/A",
                        )
                else:
                    logger.info("  Owner(s): (none found)")

        logger.info("")
        logger.info("=" * 60)
        logger.info("NOTIFICATIONS SENT")
        logger.info("=" * 60)
        logger.info(
            "  Notifications sent to owners for %d connection/owner pair(s)",
            len(notifications_sent),
        )
        if notifications_sent:
            for n in notifications_sent:
                owner_id = n.get("owner_id") or "N/A"
                logger.info(
                    "  - %s | database_id=%s | user_id=%s | %s",
                    n["connection"],
                    n["database_id"],
                    owner_id,
                    n["owner"],
                )
        else:
            logger.info(
                "  (No database connections with owners found for failed edges, or no failures)"
            )
        return 0 if not failed else 1

    except ValueError as e:
        logger.error("Configuration error: %s", e)
        return 1
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
