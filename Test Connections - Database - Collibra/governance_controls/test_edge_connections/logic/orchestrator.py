"""
Orchestrator for the governance connection testing workflow.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from governance_controls.test_edge_connections.logic.heuristic import ConnectionTestHeuristic
from governance_controls.test_edge_connections.logic.poller import JobPoller
from governance_controls.test_edge_connections.logic.impact_mapper import ImpactMapper
from governance_controls.test_edge_connections.logic.reporter import GovernanceReporter

logger = logging.getLogger(__name__)

class GovernanceOrchestrator:
    """
    Coordinates discovery, filtering, parallel testing, and impact reporting.
    """

    def __init__(
        self,
        client,
        db_manager,
        notification_handler=None,
        max_workers: int = 3,
        poll_delay: int = 5,
        job_timeout: int = 60
    ):
        self.client = client
        self.db_manager = db_manager
        self.notification_handler = notification_handler
        
        # Tools
        self.reporter = GovernanceReporter()
        self.poller = JobPoller(client, delay_seconds=poll_delay, max_total_seconds=job_timeout)
        self.mapper = ImpactMapper(client, db_manager)
        
        # Runtime Config
        self.max_workers = max_workers

    def run(self, governed_edge_ids: List[str], edge_metadata: Optional[Dict[str, Any]] = None):
        """
        Execute the full governance connection testing workflow.
        """
        edge_metadata = edge_metadata or {}
        succeeded = []
        failed = []

        self.reporter.log_header("Governance Connection Testing Started")

        total_sites = len(governed_edge_ids)
        for i, edge_id in enumerate(sorted(governed_edge_ids), 1):
            edge_name = (edge_metadata.get(edge_id) or {}).get("name", edge_id[:8] + "...")
            self.reporter.log_site_discovery(i, total_sites, edge_name, edge_id)

            # 1. Discover child connections
            try:
                all_children = self.db_manager.get_edge_site_connections(edge_site_id=edge_id)
            except Exception as e:
                logger.error("  [ERROR] Failed to fetch connections for Edge %s: %s", edge_id, e)
                failed.append({"edge_id": edge_id, "edge_name": edge_name, "error": str(e)})
                continue

            # 2. Filter testable connections via Heuristic
            testable = []
            for child in all_children:
                detail = self._get_connection_detail(child)
                if ConnectionTestHeuristic.is_testable(detail):
                    testable.append(child)
                else:
                    self.reporter.log_skip(detail.get("name"), detail.get("connectionTypeId"))

            if not testable:
                logger.info("  No testable connections found for this site.")
                continue

            # 3. Parallel testing
            site_results = self._test_connections_parallel(testable, edge_id, edge_name)

            for res in site_results:
                if res["success"]:
                    succeeded.append(res)
                else:
                    failed.append(res)

        # 4. Map Impact and Notify
        impacted_summary = self._process_failures(failed)

        # 5. Final Report
        self.reporter.print_summary(len(succeeded), len(failed), failed)
        self.reporter.print_impacted_assets(impacted_summary)

    def test_individual_connections(self, connection_ids: List[str]):
        """
        Test specific connections directly without Edge Site discovery.

        Args:
            connection_ids: List of connection IDs to test
        """
        succeeded = []
        failed = []

        self.reporter.log_header("Individual Connection Testing Started")
        logger.info("Testing %d connection(s) by ID", len(connection_ids))

        # Fetch connection details and filter testable
        testable = []
        for conn_id in connection_ids:
            try:
                detail = self.db_manager.get_connection_detail(conn_id)
                if ConnectionTestHeuristic.is_testable(detail):
                    testable.append(detail)
                else:
                    self.reporter.log_skip(detail.get("name"), detail.get("connectionTypeId"))
            except Exception as e:
                logger.error("Failed to fetch connection %s: %s", conn_id, e)
                failed.append({
                    "success": False,
                    "connection_id": conn_id,
                    "connection_name": f"Unknown ({conn_id[:8]}...)",
                    "edge_id": "cli-direct",
                    "edge_name": "Direct CLI Test",
                    "error": f"Failed to fetch connection details: {str(e)}"
                })

        # Test connections in parallel (reuse existing method)
        if testable:
            # For individual connections, use "cli-direct" as edge context
            site_results = self._test_connections_parallel(
                testable,
                edge_id="cli-direct",
                edge_name="Direct CLI Test"
            )

            for res in site_results:
                if res["success"]:
                    succeeded.append(res)
                else:
                    failed.append(res)

        # Process failures (impact mapping and notifications)
        impacted_summary = self._process_failures(failed)

        # Final report
        self.reporter.print_summary(len(succeeded), len(failed), failed)
        self.reporter.print_impacted_assets(impacted_summary)

    def test_connections_in_edge_site(
        self,
        edge_site_id: str,
        connection_ids: List[str],
        edge_metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Test specific connections within an Edge Site context.

        This method combines Edge Site context (for logging and metadata) with
        targeted connection testing (only specified connection IDs).

        Args:
            edge_site_id: Edge Site ID for context
            connection_ids: List of specific connection IDs to test
            edge_metadata: Optional metadata for the Edge Site
        """
        succeeded = []
        failed = []
        edge_metadata = edge_metadata or {}

        edge_name = (edge_metadata.get(edge_site_id) or {}).get(
            "name", f"Edge Site {edge_site_id[:8]}..."
        )

        self.reporter.log_header("Targeted Edge Site Connection Testing Started")
        logger.info("Edge Site: %s (%s)", edge_name, edge_site_id)
        logger.info("Testing %d specific connection(s)", len(connection_ids))

        # Fetch connection details and filter testable
        testable = []
        for conn_id in connection_ids:
            try:
                detail = self.db_manager.get_connection_detail(conn_id)

                # Optional: Validate that connection belongs to the Edge Site
                # Note: This is a soft validation - we'll log a warning but still test
                conn_edge_id = detail.get("edgeSiteId") or detail.get("edge_site_id")
                if conn_edge_id and conn_edge_id != edge_site_id:
                    logger.warning(
                        "  [WARNING] Connection %s belongs to different Edge Site (%s), expected %s",
                        detail.get("name", conn_id[:8]),
                        conn_edge_id[:8],
                        edge_site_id[:8]
                    )

                if ConnectionTestHeuristic.is_testable(detail):
                    testable.append(detail)
                else:
                    self.reporter.log_skip(detail.get("name"), detail.get("connectionTypeId"))
            except Exception as e:
                logger.error("Failed to fetch connection %s: %s", conn_id, e)
                failed.append({
                    "success": False,
                    "connection_id": conn_id,
                    "connection_name": f"Unknown ({conn_id[:8]}...)",
                    "edge_id": edge_site_id,
                    "edge_name": edge_name,
                    "error": f"Failed to fetch connection details: {str(e)}"
                })

        # Test connections in parallel with Edge Site context
        if testable:
            site_results = self._test_connections_parallel(
                testable,
                edge_id=edge_site_id,
                edge_name=edge_name
            )

            for res in site_results:
                if res["success"]:
                    succeeded.append(res)
                else:
                    failed.append(res)

        # Process failures (impact mapping and notifications)
        impacted_summary = self._process_failures(failed)

        # Final report
        self.reporter.print_summary(len(succeeded), len(failed), failed)
        self.reporter.print_impacted_assets(impacted_summary)

    def _get_connection_detail(self, child: Dict) -> Dict:
        """Fetch full details if possible, otherwise return the summary."""
        try:
            return self.db_manager.get_connection_detail(child.get("id"))
        except Exception:
            return child

    def _test_connections_parallel(self, testable: List[Dict], edge_id: str, edge_name: str) -> List[Dict]:
        """Test a batch of connections in parallel."""
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_conn = {
                executor.submit(self._test_single_connection, conn, edge_id, edge_name): conn 
                for conn in testable
            }
            for future in as_completed(future_to_conn):
                results.append(future.result())
        return results

    def _test_single_connection(self, connection: Dict, edge_id: str, edge_name: str) -> Dict:
        """Logic for a single connection test job."""
        conn_id = connection.get("id")
        conn_name = connection.get("name", conn_id)
        
        self.reporter.log_connection_test_start(conn_name)
        try:
            job_id = self.db_manager.test_edge_connection(edge_connection_id=conn_id)
            if not job_id:
                return self._fail_result(conn_id, conn_name, edge_id, edge_name, "No job ID returned")
            
            # Poll for completion
            res = self.poller.poll(job_id, start_as_edge=True)
            
            if res["status"] == "completed":
                self.reporter.log_connection_test_success(conn_name)
                return {"success": True, "connection_id": conn_id, "connection_name": conn_name}
            else:
                error_msg = res.get("error") or res.get("message", "Unknown error")
                self.reporter.log_connection_test_failure(conn_name, error_msg)
                return self._fail_result(conn_id, conn_name, edge_id, edge_name, error_msg)
                
        except Exception as e:
            self.reporter.log_connection_test_failure(conn_name, str(e))
            return self._fail_result(conn_id, conn_name, edge_id, edge_name, str(e))

    def _fail_result(self, conn_id, conn_name, edge_id, edge_name, error):
        return {
            "success": False, 
            "connection_id": conn_id, 
            "connection_name": conn_name, 
            "edge_id": edge_id, 
            "edge_name": edge_name, 
            "error": error
        }

    def _process_failures(self, failures: List[Dict]) -> List[Dict]:
        """Map failed connections to impacted assets and notify owners."""
        all_impacted = []
        for fail in failures:
            if not fail.get("connection_id"):
                continue
                
            impacted_list = self.mapper.get_impacted_assets_and_owners(fail["connection_id"])
            
            for item in impacted_list:
                conn = item["connection"]
                
                # Create a reporting-friendly summary
                report_item = {
                    "connection_name": conn.name,
                    "database_id": conn.database_id,
                    "owners": item["owners"],
                    "error": fail["error"]
                }
                all_impacted.append(report_item)
                
                # Notification
                if self.notification_handler:
                    impact_msg = f"Impact alert: Source connection '{fail['edge_name']}' failed. Error: {fail['error']}"
                    for owner in item["owners"]:
                        # notify expects DatabaseConnection object
                        self.notification_handler.notify(conn, impact_msg, owner)
                        self.reporter.log_impact_alert(conn.name, fail["edge_name"], owner.get("email", "unknown"))
                        
        return all_impacted
