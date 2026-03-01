"""
Job poller for monitoring Collibra jobs.
"""

import logging
import time
from typing import Any, Dict, Optional

from collibra_client.core.exceptions import CollibraAPIError

logger = logging.getLogger(__name__)

class JobPoller:
    """
    Handles polling jobs from both Collibra REST and GraphQL APIs.
    """

    def __init__(
        self,
        client,
        max_attempts: int = 150,
        delay_seconds: int = 5,
        max_submitted_seconds: int = 60,
        max_total_seconds: int = 60
    ):
        self.client = client
        self.max_attempts = max_attempts
        self.delay_seconds = delay_seconds
        self.max_submitted_seconds = max_submitted_seconds
        self.max_total_seconds = max_total_seconds

    def poll(self, job_id: str, start_as_edge: bool = True) -> Dict[str, Any]:
        """
        Poll job status until terminal state.
        
        Args:
            job_id: The ID of the job to monitor.
            start_as_edge: If True, starts with GraphQL polling (Edge sites).
            
        Returns:
            Dictionary with final status and message.
        """
        is_edge_job = start_as_edge
        submitted_start_time = None
        start_time = time.time()
        
        for attempt in range(self.max_attempts):
            # Global timeout check
            if self.max_total_seconds and (time.time() - start_time) > self.max_total_seconds:
                return {"status": "failed", "message": f"Job timed out after {self.max_total_seconds}s"}
            
            try:
                job_status = self._fetch_status(job_id, is_edge_job)
                
                # If still empty after fallback, it might just be too early
                if not job_status:
                    if attempt < self.max_attempts - 1:
                        time.sleep(self.delay_seconds)
                        continue
                    return {"status": "error", "message": "Job not found in REST or GraphQL APIs"}

                status_info = self._parse_status(job_status)
                status_upper = status_info["status_upper"]
                
                # Handle SUBMITTED state with specific timeout
                if status_upper == "SUBMITTED":
                    if submitted_start_time is None:
                        submitted_start_time = time.time()
                    elif self.max_submitted_seconds and (time.time() - submitted_start_time) > self.max_submitted_seconds:
                        return {"status": "failed", "message": f"Job stuck in SUBMITTED for >{self.max_submitted_seconds}s"}
                elif status_upper != "UNKNOWN":
                    submitted_start_time = None

                # Check for terminal states
                if status_upper in ["COMPLETED", "SUCCESS", "SUCCEEDED", "CAPABILITY_SUCCEEDED", "DONE", "FINISHED"]:
                    return {"status": "completed", "message": status_info["message"]}
                
                if status_upper in ["FAILED", "ERROR", "CAPABILITY_FAILED", "CANCELLED", "CANCELED"]:
                    return self._handle_failure(job_id, job_status, status_info["message"])

                # Intermediate logging
                if attempt % 1 == 0:  # Log every attempt for clear terminal progress
                    logger.info("  [%s] Status: %s", job_id[:8], status_upper)

                if attempt < self.max_attempts - 1:
                    time.sleep(self.delay_seconds)
                    
            except Exception as e:
                logger.debug("  Polling error on attempt %d: %s", attempt, e)
                if attempt < self.max_attempts - 1:
                    time.sleep(self.delay_seconds)
                else:
                    return {"status": "error", "message": f"Final polling error: {e}"}
                    
        return {
            "status": "timeout",
            "message": f"Job did not complete within {self.max_attempts * self.delay_seconds} seconds",
        }

    def _fetch_status(self, job_id: str, is_edge_job: bool) -> Optional[Dict]:
        """Fetch status using appropriate API."""
        if not is_edge_job:
            try:
                return self.client.get_job_status(job_id)
            except CollibraAPIError as e:
                if e.status_code == 404:
                    return self.client.get_edge_job_status(job_id)
                raise e
        return self.client.get_edge_job_status(job_id)

    def _parse_status(self, job_status: Dict) -> Dict:
        """Extract status and message from job response."""
        status = (
            job_status.get("status")
            or job_status.get("state")
            or job_status.get("jobStatus")
            or job_status.get("currentStatus")
            or "UNKNOWN"
        )
        message = (
            job_status.get("message")
            or job_status.get("statusMessage")
            or ""
        )
        return {"status_upper": str(status).upper(), "message": message}

    def _handle_failure(self, job_id: str, job_status: Dict, message: str) -> Dict:
        """Standardize failure response and log details."""
        logger.debug("  Full Job Status on Failure (%s): %s", job_id, job_status)

        # Extract detailed error information
        error_msg = (
            job_status.get("error")
            or job_status.get("errorMessage")
            or job_status.get("failureMessage")
            or message
        )

        # If still no error message, check if it's actually in the message field as a structured object
        if not error_msg or error_msg == "":
            if message:
                error_msg = message
            else:
                error_msg = "Connection test failed (no error details provided)"

        # Clean up the error message if it's too verbose
        if isinstance(error_msg, str):
            # Extract the key part of common error patterns
            if "Connection refused" in error_msg or "timed out" in error_msg:
                error_msg = "Network connectivity issue - " + error_msg.split('\n')[0]
            elif "authentication" in error_msg.lower() or "credential" in error_msg.lower():
                error_msg = "Authentication/credential issue - " + error_msg.split('\n')[0]
            elif "not found" in error_msg.lower():
                error_msg = "Resource not found - " + error_msg.split('\n')[0]

        return {"status": "failed", "message": error_msg, "error": error_msg}
