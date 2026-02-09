"""
Script to test database connections and notify owners of failures.

This script:
1. Fetches all database connections from Collibra
2. Tests each connection
3. Notifies owners if credentials have changed and sync failed
"""

import sys
import time
import json
from typing import List, Dict, Any, Optional

from collibra_client import (
    CollibraClient,
    CollibraConfig,
    DatabaseConnectionManager,
    ConsoleNotificationHandler,
    CollibraNotificationHandler,
    get_connection_owner,
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
            print(f"    ⚠ Could not fetch user details for owner {owner_id}: {e}")
            return {
                "owner_id": owner_id,
                "email": None,
                "username": None,
                "name": None,
            }
            
    except Exception as e:
        print(f"    ⚠ Could not fetch database asset details: {e}")
        return None


def test_all_database_connections(
    client: CollibraClient,
    db_manager: DatabaseConnectionManager,
    notification_handler,
    notify_only_on_credential_errors: bool = True,
) -> Dict[str, Any]:
    """
    Test all database connections and notify owners of failures.

    Args:
        client: CollibraClient instance for API calls.
        db_manager: DatabaseConnectionManager instance.
        notification_handler: Notification handler instance.
        notify_only_on_credential_errors: If True, only notify on credential errors.
                                         If False, notify on all failures.

    Returns:
        Dictionary containing test results summary.
    """
    # Refresh database connections first to synchronize all connections from data source
    print("Refreshing database connections to synchronize with data source...")
    
    # First, get a preliminary list to find unique edge connection IDs for refreshing
    try:
        preliminary_connections = db_manager.list_database_connections(limit=500)
        edge_connection_ids = set(conn.edge_connection_id for conn in preliminary_connections)
        
        if edge_connection_ids:
            print(f"Found {len(edge_connection_ids)} unique edge connection(s)")
            print("Refreshing each edge connection to synchronize all database connections...")
            refreshed_count = 0
            for edge_id in edge_connection_ids:
                try:
                    db_manager.refresh_database_connections(edge_connection_id=edge_id)
                    refreshed_count += 1
                except Exception as e:
                    print(f"  ⚠ Could not refresh edge connection {edge_id[:8]}...: {e}")
            print(f"✓ Refreshed {refreshed_count}/{len(edge_connection_ids)} edge connection(s)\n")
        else:
            # Try refreshing without edge_connection_id (might work for some API versions)
            try:
                refresh_result = db_manager.refresh_database_connections()
                print("✓ Database connections refresh initiated\n")
            except Exception as e:
                print(f"⚠ Warning: Could not refresh connections: {e}")
                print("  Continuing to list existing connections...\n")
    except Exception as e:
        print(f"⚠ Warning: Could not refresh connections: {e}")
        print("  Continuing to list existing connections...\n")
    
    # Fetch all database connections (now includes all synchronized connections after refresh)
    print("Fetching all database connections...")
    try:
        all_connections = db_manager.list_database_connections()
        
        # Filter to only connections with both edge connection ID and database asset ID
        connections = [conn for conn in all_connections if conn.database_id is not None]
        
        print(f"Found {len(all_connections)} total database connections")
        print(f"Filtered to {len(connections)} connection(s) with both edge connection ID and database asset ID\n")
    except Exception as e:
        print(f"Error fetching database connections: {e}")
        return {
            "total": 0,
            "tested": 0,
            "successful": 0,
            "failed": 0,
            "notified": 0,
            "errors": [str(e)],
        }

    results = {
        "total_all": len(all_connections),
        "total": len(connections),
        "tested": 0,
        "successful": 0,
        "failed": 0,
        "notified": 0,
        "failures": [],
    }

    for connection in connections:
        print(f"Testing connection: {connection.name} (ID: {connection.id})")
        print(f"  Database Asset ID: {connection.database_id}")
        results["tested"] += 1

        # Test the database connection first
        test_result = db_manager.test_database_connection(connection.id)

        if test_result["success"]:
            print(f"  ✓ Connection test successful")
            
            # If connection test is successful and we have a database_id, synchronize metadata
            if connection.database_id:
                print(f"  Synchronizing database metadata...")
                try:
                    sync_result = db_manager.synchronize_database_metadata(connection.database_id)
                    job_id = sync_result.get("jobId") or sync_result.get("id")
                    
                    if job_id:
                        print(f"  ✓ Synchronization job started (Job ID: {job_id})")
                        
                        # Monitor job status
                        max_attempts = 10
                        attempt = 0
                        job_completed = False
                        
                        while attempt < max_attempts and not job_completed:
                            time.sleep(2)  # Wait 2 seconds between checks
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
                                        print(f"    Job message details:")
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
                                
                                print(f"    Job status: {status_display}")
                                
                                # Check for completion statuses (case-insensitive)
                                status_upper = str(status).upper()
                                if status_upper in ["SUCCESS", "COMPLETED", "FINISHED", "DONE"]:
                                    job_completed = True
                                    print(f"  ✓ Metadata synchronization completed successfully")
                                    if message_parsed:
                                        success = message_parsed.get("success", True)
                                        if success:
                                            print(f"    Database: {message_parsed.get('assetName', 'N/A')}")
                                    results["successful"] += 1
                                elif status_upper in ["FAILED", "ERROR", "CANCELLED", "CANCELED"]:
                                    job_completed = True
                                    error_msg = (
                                        job_status.get("error") or 
                                        job_status.get("errorMessage") or 
                                        (message_parsed.get("statusMessage") if message_parsed else None) or
                                        message_raw or 
                                        "Unknown error"
                                    )
                                    print(f"  ✗ Metadata synchronization failed: {error_msg}")
                                    
                                    # Fetch owner information for failed job
                                    print(f"  Fetching database asset owner information...")
                                    owner_info = get_database_owner_info(
                                        client, db_manager, connection.database_id
                                    )
                                    
                                    if owner_info:
                                        print(f"    Owner: {owner_info.get('name', 'N/A')}")
                                        if owner_info.get("email"):
                                            print(f"    Email: {owner_info.get('email')}")
                                        if owner_info.get("username"):
                                            print(f"    Username: {owner_info.get('username')}")
                                    else:
                                        print(f"    ⚠ Could not retrieve owner information")
                                    
                                    results["failed"] += 1
                                    results["failures"].append({
                                        "connection_id": connection.id,
                                        "connection_name": connection.name,
                                        "database_id": connection.database_id,
                                        "error": f"Synchronization failed: {error_msg}",
                                        "is_credential_error": False,
                                        "notified": False,
                                        "owner_info": owner_info,
                                    })
                            except Exception as e:
                                print(f"    ⚠ Could not check job status: {e}")
                                if attempt >= max_attempts:
                                    print(f"  ⚠ Job monitoring timeout - check job status manually")
                        else:
                            if not job_completed:
                                print(f"  ⚠ Job still running after {max_attempts} checks - monitor manually")
                                results["successful"] += 1  # Count as success if we can't determine final status
                    else:
                        print(f"  ⚠ Synchronization started but no job ID returned")
                        results["successful"] += 1
                        
                except Exception as e:
                    print(f"  ✗ Synchronization failed: {e}")
                    
                    # Fetch owner information for failed synchronization
                    if connection.database_id:
                        print(f"  Fetching database asset owner information...")
                        owner_info = get_database_owner_info(
                            client, db_manager, connection.database_id
                        )
                        
                        if owner_info:
                            print(f"    Owner: {owner_info.get('name', 'N/A')}")
                            if owner_info.get("email"):
                                print(f"    Email: {owner_info.get('email')}")
                            if owner_info.get("username"):
                                print(f"    Username: {owner_info.get('username')}")
                        else:
                            print(f"    ⚠ Could not retrieve owner information")
                    else:
                        owner_info = None
                    
                    results["failed"] += 1
                    results["failures"].append({
                        "connection_id": connection.id,
                        "connection_name": connection.name,
                        "database_id": connection.database_id,
                        "error": f"Synchronization request failed: {e}",
                        "is_credential_error": False,
                        "notified": False,
                        "owner_info": owner_info,
                    })
            else:
                print(f"  ⚠ No database asset ID - skipping synchronization")
                results["successful"] += 1
            print()
        else:
            # Connection test failed - don't attempt synchronization
            print(f"  ✗ Connection test failed: {test_result['message']}\n")
            results["failed"] += 1

            # Check if this is a credential error
            is_credential_error = test_result.get("is_credential_error", False)

            # Notify owner if appropriate
            should_notify = (
                not notify_only_on_credential_errors or is_credential_error
            )

            if should_notify:
                # Get owner information
                owner_info = get_connection_owner(client, connection)

                # Send notification
                notification_sent = notification_handler.notify(
                    connection=connection,
                    error_message=test_result["message"],
                    owner_info=owner_info,
                )

                if notification_sent:
                    results["notified"] += 1

            # Record failure details
            results["failures"].append(
                {
                    "connection_id": connection.id,
                    "connection_name": connection.name,
                    "database_id": connection.database_id,
                    "error": test_result["message"],
                    "is_credential_error": is_credential_error,
                    "notified": should_notify and notification_sent if should_notify else False,
                }
            )

    return results


def main():
    """Main function to run database connection tests."""
    try:
        # Load configuration from environment variables
        print("Loading configuration...")
        config = CollibraConfig.from_env()

        # Note: We're using OAuth token, Basic Auth credentials are optional

        # Create Collibra client (OAuth)
        print("Initializing Collibra client...")
        client = CollibraClient(
            base_url=config.base_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
            timeout=config.timeout,
        )

        # Test OAuth connection
        print("Testing OAuth connection...")
        if not client.test_connection():
            print("Error: Failed to connect to Collibra API")
            sys.exit(1)
        print("✓ OAuth connection successful\n")

        # Create database connection manager (using OAuth token)
        print("Initializing database connection manager...")
        db_manager = DatabaseConnectionManager(
            client=client,
            use_oauth=True,  # Use OAuth Bearer token instead of Basic Auth
        )

        # Create notification handler
        # Use ConsoleNotificationHandler for testing, or CollibraNotificationHandler for production
        notification_handler = ConsoleNotificationHandler()
        # notification_handler = CollibraNotificationHandler(client)

        # Test all database connections
        print("=" * 60)
        print("DATABASE CONNECTION TESTING")
        print("=" * 60)
        print()

        results = test_all_database_connections(
            client=client,
            db_manager=db_manager,
            notification_handler=notification_handler,
            notify_only_on_credential_errors=True,
        )

        # Print summary
        print()
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total connections fetched: {results.get('total_all', results['total'])}")
        print(f"Connections with both edge connection ID and database asset ID: {results['total']}")
        print(f"Tested: {results['tested']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        print(f"Notifications sent: {results['notified']}")

        if results["failures"]:
            print("\nFailed connections:")
            for failure in results["failures"]:
                print(f"  - {failure['connection_name']}: {failure['error']}")

        # Exit with error code if any failures occurred
        if results["failed"] > 0:
            sys.exit(1)

    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

