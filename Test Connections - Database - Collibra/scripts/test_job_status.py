"""
Simple script to test job status API and see the response structure.
"""

import sys
import json

from collibra_client import (
    CollibraClient,
    CollibraConfig,
)


def test_job_status(job_id: str):
    """Test getting job status for a specific job ID."""
    print("=" * 60)
    print("JOB STATUS TEST")
    print("=" * 60)
    print()

    try:
        # Load configuration
        print("Loading configuration from environment variables...")
        config = CollibraConfig.from_env()
        print(f"✓ Base URL: {config.base_url}")
        print()

        # Create OAuth client
        print("Creating Collibra OAuth client...")
        client = CollibraClient(
            base_url=config.base_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
            timeout=config.timeout,
        )
        print("✓ OAuth client created")

        # Test OAuth connection
        print("\nTesting OAuth connection...")
        if not client.test_connection():
            print("✗ OAuth connection failed")
            return False
        print("✓ OAuth connection successful")
        print()

        # Get job status
        print(f"Fetching job status for Job ID: {job_id}")
        print("-" * 60)
        
        try:
            job_status = client.get_job_status(job_id)
            
            print("\nJob Status Response:")
            print("=" * 60)
            print(json.dumps(job_status, indent=2))
            print("=" * 60)
            print()
            
            # Try to extract common fields
            print("Extracted Fields:")
            print("-" * 60)
            print(f"Status: {job_status.get('status', 'N/A')}")
            print(f"State: {job_status.get('state', 'N/A')}")
            print(f"Job Status: {job_status.get('jobStatus', 'N/A')}")
            print(f"Current Status: {job_status.get('currentStatus', 'N/A')}")
            print(f"Progress: {job_status.get('progress', 'N/A')}")
            print(f"Progress Percentage: {job_status.get('progressPercentage', 'N/A')}")
            print(f"Completion Percentage: {job_status.get('completionPercentage', 'N/A')}")
            print(f"Message: {job_status.get('message', 'N/A')}")
            print(f"Status Message: {job_status.get('statusMessage', 'N/A')}")
            print(f"Error: {job_status.get('error', 'N/A')}")
            print(f"Error Message: {job_status.get('errorMessage', 'N/A')}")
            print()
            
            print("=" * 60)
            print("✓ TEST COMPLETED")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n✗ Error fetching job status: {e}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_job_status.py <job_id>")
        print("\nExample:")
        print("  python3 test_job_status.py 019c41d0-b593-74a4-a236-4a80e21765c3")
        sys.exit(1)
    
    job_id = sys.argv[1]
    success = test_job_status(job_id)
    sys.exit(0 if success else 1)

