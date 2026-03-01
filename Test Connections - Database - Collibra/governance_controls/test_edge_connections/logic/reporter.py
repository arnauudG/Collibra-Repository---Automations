"""
Reporter for generating human-friendly logs and summaries.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class GovernanceReporter:
    """
    Handles human-friendly logging and structured reporting for connection tests.
    """

    def log_header(self, title: str):
        """Print a standardized section header."""
        logger.info("")
        logger.info("=" * 80)
        logger.info("  " + title.upper())
        logger.info("=" * 80)

    def log_site_discovery(self, index: int, total: int, edge_name: str, edge_id: str):
        """Log the start of connection discovery for an edge site."""
        logger.info("")
        logger.info("[%d/%d] Edge Site: %s", index, total, edge_name)
        logger.info("       ID: %s", edge_id[:16] + "...")

    def log_connection_test_start(self, connection_name: str):
        """Log the start of a connection test."""
        logger.info("    ⏳ Testing: %s", connection_name)

    def log_connection_test_success(self, connection_name: str):
        """Log a successful connection test."""
        logger.info("    ✅ PASSED: %s", connection_name)

    def log_connection_test_failure(self, connection_name: str, error_msg: str):
        """Log a failed connection test."""
        # Use INFO instead of WARNING for cleaner output - failures are expected
        logger.info("    ❌ FAILED: %s", connection_name)
        logger.info("       Reason: %s", error_msg)

    def log_skip(self, connection_name: str, connection_type: str):
        """Log a skipped connection."""
        logger.info("    ⊘  SKIPPED: %s (Type: %s - not testable)", connection_name, connection_type)

    def log_impact_alert(self, connection_name: str, edge_name: str, owner_email: str):
        """Log an impact alert notification."""
        logger.info("    📧 Alert sent to: %s", owner_email)

    def print_summary(self, succeeded_count: int, failed_count: int, failed_details: List[Dict[str, Any]]):
        """Print the final summary report."""
        self.log_header("TEST RESULTS SUMMARY")

        total = succeeded_count + failed_count
        success_rate = (succeeded_count / total * 100) if total > 0 else 0

        logger.info("")
        logger.info("  Total Connections Tested: %d", total)
        logger.info("  ✅ Passed: %d connection(s)", succeeded_count)
        logger.info("  ❌ Failed: %d connection(s)", failed_count)
        logger.info("  📊 Success Rate: %.1f%%", success_rate)
        logger.info("")

        if failed_details:
            logger.info("  Failed Connection Details:")
            logger.info("  " + "-" * 76)
            for i, detail in enumerate(failed_details, 1):
                logger.info("")
                logger.info("  %d. Connection: %s", i, detail.get("connection_name"))
                logger.info("     Edge ID: %s", detail.get("edge_id", "")[:16] + "...")
                logger.info("     Error: %s", detail.get("error"))
        else:
            logger.info("  🎉 All connections passed!")

        logger.info("")
        logger.info("=" * 80)

    def print_impacted_assets(self, impacted_assets: List[Dict[str, Any]]):
        """Print details about impacted assets and their owners."""
        if not impacted_assets:
            logger.info("")
            logger.info("ℹ️  No database assets were impacted by connection failures.")
            return

        logger.info("")
        self.log_header("IMPACTED DATABASES & OWNER NOTIFICATIONS")
        logger.info("")

        for i, item in enumerate(impacted_assets, 1):
            logger.info("  %d. Database Connection: %s", i, item["connection_name"])
            logger.info("     Database Asset ID: %s", item["database_id"])
            logger.info("     Failure Reason: %s", item.get("error", "Unknown error"))
            logger.info("")

            if item["owners"]:
                logger.info("     📧 Notified Owner(s):")
                for o in item["owners"]:
                    owner_name = o.get("name") or o.get("username") or "Unknown"
                    owner_email = o.get("email") or "No email available"
                    logger.info("        • %s (%s)", owner_name, owner_email)
            else:
                logger.info("     ⚠️  No owners found for this database asset")

            logger.info("     " + "-" * 72)
            logger.info("")

        logger.info("=" * 80)
