"""
Simple script to test database metadata synchronization.

This script:
1. Fetches database connections with both edge connection ID and database asset ID
2. Synchronizes metadata for each database asset
3. Monitors job status until completion
"""

import sys
import time
import json
from typing import Optional, Dict, Any

from collibra_client import (
    CollibraClient,
    CollibraConfig,
    DatabaseConnectionManager,
)


def parse_job_message(message: str) -> Optional[Dict[str, Any]]:
    """
    Parse the job status message (which is a JSON string).
    
    Args:
        message: JSON string containing job details.
        
    Returns:
        Parsed message dictionary or None if parsing fails.
    """
    if not message:
        return None
    
    try:
        return json.loads(message)
    except (json.JSONDecodeError, TypeError):
        return None


def get_database_owner_info(
    client: CollibraClient,
    db_manager: DatabaseConnectionManager,
    database_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get database asset owner information from Catalog Database API.
    
    Cataloged databases always have one or several owners in the ownerIds array.
    
    Args:
        client: CollibraClient instance.
        db_manager: DatabaseConnectionManager instance.
        database_id: UUID of the database asset.
        
    Returns:
        Dictionary containing owner information with keys:
        - owner_id: Owner user ID (first owner from ownerIds array)
        - email: Owner email address
        - username: Owner username
        - name: Owner full name
        Or None if owner information cannot be retrieved.
    """
    try:
        # Get database asset from Catalog Database API
        # Cataloged databases always have one or several owners in ownerIds array
        db_asset = db_manager.get_database_asset(database_id)
        
        # Catalog Database API returns ownerIds as an array (per API documentation)
        owner_ids = db_asset.get("ownerIds")
        
        if not owner_ids or not isinstance(owner_ids, list) or len(owner_ids) == 0:
            return None
        
        # Use the first owner from the array
        owner_id = owner_ids[0]
        
        # Get user details
        try:
            user = client.get_user(owner_id)
            return {
                "owner_id": owner_id,
                "email": user.get("email") or user.get("emailAddress"),
                "username": user.get("username"),
                "name": (
                    f"{user.get('firstName', '')} {user.get('lastName', '')}".strip() 
                    or user.get("fullName") 
                    or user.get("username")
                ),
            }
        except Exception as e:
            print(f"   ⚠ Could not fetch user details for owner {owner_id}: {e}")
            return {
                "owner_id": owner_id,
                "email": None,
                "username": None,
                "name": None,
            }
            
    except Exception as e:
        print(f"   ⚠ Could not fetch database asset details: {e}")
        return None


def synchronize_databases():
    """Test synchronizing database metadata."""
    print("=" * 60)
    print("DATABASE METADATA SYNCHRONIZATION TEST")
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

        # Create database connection manager
        print("Creating database connection manager...")
        db_manager = DatabaseConnectionManager(
            client=client,
            use_oauth=True,
        )
        print("✓ Database manager created")
        print()

        # Refresh connections first
        print("Refreshing database connections...")
        try:
            preliminary_connections = db_manager.list_database_connections(limit=500)
            edge_connection_ids = set(conn.edge_connection_id for conn in preliminary_connections)
            
            if edge_connection_ids:
                print(f"Found {len(edge_connection_ids)} unique edge connection(s)")
                refreshed_count = 0
                for edge_id in edge_connection_ids:
                    try:
                        db_manager.refresh_database_connections(edge_connection_id=edge_id)
                        refreshed_count += 1
                    except Exception as e:
                        print(f"  ⚠ Could not refresh edge connection {edge_id[:8]}...: {e}")
                print(f"✓ Refreshed {refreshed_count}/{len(edge_connection_ids)} edge connection(s)\n")
        except Exception as e:
            print(f"⚠ Warning: Could not refresh connections: {e}\n")

        # Fetch connections with both edge connection ID and database asset ID
        print("Fetching database connections...")
        all_connections = db_manager.list_database_connections()
        connections = [conn for conn in all_connections if conn.database_id is not None]
        
        print(f"✓ Found {len(all_connections)} total connections")
        print(f"✓ Filtered to {len(connections)} connections with both edge connection ID and database asset ID\n")

        if len(connections) == 0:
            print("⚠ No database connections found with both edge connection ID and database asset ID.")
            return False

        # Synchronize each database
        print("=" * 60)
        print("SYNCHRONIZING DATABASE METADATA")
        print("=" * 60)
        print()

        sync_results = []

        for i, connection in enumerate(connections, 1):
            print(f"{i}. {connection.name}")
            print(f"   Database Asset ID: {connection.database_id}")
            print(f"   Connection ID: {connection.id}")
            
            try:
                # Synchronize metadata
                sync_result = db_manager.synchronize_database_metadata(connection.database_id)
                job_id = sync_result.get("jobId") or sync_result.get("id")
                
                if job_id:
                    print(f"   ✓ Synchronization job started (Job ID: {job_id})")
                    
                    # Monitor job status
                    max_attempts = 20  # Allow more time for synchronization
                    attempt = 0
                    job_completed = False
                    
                    while attempt < max_attempts and not job_completed:
                        time.sleep(3)  # Wait 3 seconds between checks
                        attempt += 1
                        
                        try:
                            job_status = client.get_job_status(job_id)
                            
                            # Handle different possible field names for status
                            status = (
                                job_status.get("status") or 
                                job_status.get("state") or 
                                job_status.get("jobStatus") or
                                job_status.get("currentStatus") or
                                "UNKNOWN"
                            )
                            
                            # Handle different possible field names for progress
                            progress = (
                                job_status.get("progress") or 
                                job_status.get("progressPercentage") or
                                job_status.get("completionPercentage") or
                                0
                            )
                            
                            # Get and parse message
                            message_raw = job_status.get("message") or job_status.get("statusMessage") or ""
                            message_parsed = parse_job_message(message_raw)
                            
                            if attempt == 1:
                                # Print parsed message details on first check
                                if message_parsed:
                                    print(f"   → Job message details:")
                                    if message_parsed.get("statusMessage"):
                                        print(f"      Status: {message_parsed.get('statusMessage')}")
                                    if message_parsed.get("assetName"):
                                        print(f"      Asset: {message_parsed.get('assetName')}")
                                    if message_parsed.get("success") is not None:
                                        print(f"      Success: {message_parsed.get('success')}")
                            
                            status_display = f"{status}"
                            if progress:
                                status_display += f" (Progress: {progress}%)"
                            if message_parsed and message_parsed.get("statusMessage"):
                                status_display += f" - {message_parsed.get('statusMessage')}"
                            elif message_raw and not message_parsed:
                                # If message is not JSON, show raw message (truncated)
                                status_display += f" - {message_raw[:100]}"
                            
                            print(f"   → Job status: {status_display}")
                            
                            # Check for completion statuses (case-insensitive)
                            status_upper = str(status).upper()
                            if status_upper in ["SUCCESS", "COMPLETED", "FINISHED", "DONE"]:
                                job_completed = True
                                print(f"   ✓ Metadata synchronization completed successfully")
                                if message_parsed:
                                    success = message_parsed.get("success", True)
                                    if success:
                                        print(f"      Database: {message_parsed.get('assetName', 'N/A')}")
                                print()
                                sync_results.append({
                                    "connection": connection.name,
                                    "database_id": connection.database_id,
                                    "job_id": job_id,
                                    "status": "SUCCESS",
                                })
                            elif status_upper in ["FAILED", "ERROR", "CANCELLED", "CANCELED"]:
                                job_completed = True
                                error_msg = (
                                    job_status.get("error") or 
                                    job_status.get("errorMessage") or 
                                    (message_parsed.get("statusMessage") if message_parsed else None) or
                                    message_raw or 
                                    "Unknown error"
                                )
                                print(f"   ✗ Metadata synchronization failed: {error_msg}")
                                
                                # Fetch owner information for failed job
                                print(f"   Fetching database asset owner information...")
                                owner_info = get_database_owner_info(
                                    client, db_manager, connection.database_id
                                )
                                
                                if owner_info:
                                    print(f"      Owner: {owner_info.get('name', 'N/A')}")
                                    if owner_info.get("email"):
                                        print(f"      Email: {owner_info.get('email')}")
                                    if owner_info.get("username"):
                                        print(f"      Username: {owner_info.get('username')}")
                                else:
                                    print(f"      ⚠ Could not retrieve owner information")
                                print()
                                
                                sync_results.append({
                                    "connection": connection.name,
                                    "database_id": connection.database_id,
                                    "job_id": job_id,
                                    "status": "FAILED",
                                    "error": error_msg,
                                    "owner_info": owner_info,
                                })
                        except Exception as e:
                            print(f"   ⚠ Could not check job status: {e}")
                            if attempt >= max_attempts:
                                print(f"   ⚠ Job monitoring timeout\n")
                    
                    if not job_completed:
                        print(f"   ⚠ Job still running after {max_attempts} checks - monitor manually\n")
                        sync_results.append({
                            "connection": connection.name,
                            "database_id": connection.database_id,
                            "job_id": job_id,
                            "status": "RUNNING",
                        })
                else:
                    print(f"   ⚠ Synchronization started but no job ID returned\n")
                    sync_results.append({
                        "connection": connection.name,
                        "database_id": connection.database_id,
                        "status": "UNKNOWN",
                    })
                    
            except Exception as e:
                print(f"   ✗ Synchronization failed: {e}")
                
                # Fetch owner information for failed synchronization
                if connection.database_id:
                    print(f"   Fetching database asset owner information...")
                    owner_info = get_database_owner_info(
                        client, db_manager, connection.database_id
                    )
                    
                    if owner_info:
                        print(f"      Owner: {owner_info.get('name', 'N/A')}")
                        if owner_info.get("email"):
                            print(f"      Email: {owner_info.get('email')}")
                        if owner_info.get("username"):
                            print(f"      Username: {owner_info.get('username')}")
                    else:
                        print(f"      ⚠ Could not retrieve owner information")
                else:
                    owner_info = None
                print()
                
                sync_results.append({
                    "connection": connection.name,
                    "database_id": connection.database_id,
                    "status": "ERROR",
                    "error": str(e),
                    "owner_info": owner_info,
                })

        # Summary
        print("=" * 60)
        print("SYNCHRONIZATION SUMMARY")
        print("=" * 60)
        print()
        
        success_count = sum(1 for r in sync_results if r.get("status") == "SUCCESS")
        failed_count = sum(1 for r in sync_results if r.get("status") in ["FAILED", "ERROR"])
        running_count = sum(1 for r in sync_results if r.get("status") == "RUNNING")
        
        print(f"Total databases synchronized: {len(sync_results)}")
        print(f"  ✓ Successful: {success_count}")
        print(f"  ✗ Failed: {failed_count}")
        print(f"  ⏳ Still running: {running_count}")
        print()

        if failed_count > 0:
            print("Failed synchronizations:")
            for result in sync_results:
                if result.get("status") in ["FAILED", "ERROR"]:
                    print(f"  - {result['connection']}: {result.get('error', 'Unknown error')}")
            print()

        print("=" * 60)
        print("✓ TEST COMPLETED")
        print("=" * 60)
        
        return True

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = synchronize_databases()
    sys.exit(0 if success else 1)

