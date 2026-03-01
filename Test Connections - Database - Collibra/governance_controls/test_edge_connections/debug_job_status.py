#!/usr/bin/env python3
"""
Debug utility to check the status of a Collibra job via REST and GraphQL APIs.

Usage:
    uv run python governance_controls/test_edge_connections/debug_job_status.py <JOB_ID>

The script probes the job through two APIs:
  1. REST Jobs API (/rest/jobs/v1/jobs/<id>) — for Catalog jobs
  2. Edge GraphQL API (jobById query) — for Edge connection test jobs

This is useful for diagnosing stuck, failed, or unknown jobs during development.
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
        description="Debug a Collibra job status via REST and GraphQL APIs."
    )
    parser.add_argument("job_id", help="The UUID of the job to diagnose")
    args = parser.parse_args()

    from collibra_client import CollibraClient, CollibraConfig

    config = CollibraConfig.from_env()
    client = CollibraClient(
        base_url=config.base_url,
        client_id=config.client_id,
        client_secret=config.client_secret,
    )

    job_id = args.job_id
    logger.info("Diagnosing Job: %s", job_id)

    # 1. Try REST Jobs API
    logger.info("Checking REST /rest/jobs/v1/jobs/%s ...", job_id)
    try:
        rest_status = client.get(f"/rest/jobs/v1/jobs/{job_id}")
        print("REST Response:")
        print(json.dumps(rest_status, indent=2))
    except Exception as e:
        logger.warning("REST API: %s", e)

    print()

    # 2. Try Edge GraphQL jobById
    logger.info("Checking GraphQL jobById ...")
    query = """
    query TestConnectionStatus($jobId: ID!) {
      job: jobById(id: $jobId) {
        status
        message
      }
    }
    """
    variables = {"jobId": job_id}
    try:
        gql_response = client.post_graphql(
            "/edge/api/graphql",
            query,
            variables=variables,
            operation_name="TestConnectionStatus",
        )
        print("GraphQL Response:")
        print(json.dumps(gql_response, indent=2))
    except Exception as e:
        logger.warning("GraphQL API: %s", e)

    return 0


if __name__ == "__main__":
    sys.exit(main())
