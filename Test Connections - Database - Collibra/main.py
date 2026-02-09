#!/usr/bin/env python3
"""
Main orchestrator script for Collibra Database Connection Testing.

This script orchestrates the complete workflow:
1. Tests OAuth connection
2. Lists all database connections
3. Synchronizes metadata for each database
4. Monitors job status
5. Fetches and displays owners for failing databases
6. Provides comprehensive summary report
7. Prepares notification data structure (stored in variable)

The notification data structure contains:
- Database name, ID, and connection ID
- Error message
- Owner information (name, email, username, owner ID) - supports multiple owners
- Pre-formatted notification messages

Usage:
    python3 main.py

Output:
    Returns notification_data dictionary variable containing all failed databases
    and their owner information, ready for use in notification systems.
    
    Example structure:
    {
        "generated_at": "2024-01-01T12:00:00",
        "total_failed": 3,
        "failed_databases": [
            {
                "database": {"name": "...", "database_id": "...", "connection_id": "..."},
                "error": "...",
                "owners": [{"owner_id": "...", "name": "...", "email": "..."}],
                "notification_message": "Hello,\n\nWe wanted to inform you..."
            }
        ]
    }
"""

import sys
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from collibra_client import (
    CollibraClient,
    CollibraConfig,
    DatabaseConnectionManager,
    ConsoleNotificationHandler,
    get_connection_owner,
)


def parse_job_message(message: str) -> Optional[Dict[str, Any]]:
    """Parse the job status message (which is a JSON string)."""
    if not message:
        return None
    try:
        return json.loads(message)
    except (json.JSONDecodeError, TypeError):
        return None


def prepare_notification_data(
    failed_databases: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Prepare notification data structure from failed databases.

    This function structures the failed database information into a format
    suitable for notification systems. The data is returned as a dictionary
    that can be used directly for notifications (email, Slack, etc.) or
    serialized to JSON if needed.

    Args:
        failed_databases: List of dictionaries containing failed database information.

    Returns:
        Dictionary containing structured notification data with keys:
        - generated_at: ISO timestamp of when data was generated
        - total_failed: Number of failed databases
        - failed_databases: List of failed database dictionaries, each containing:
          - database: Dict with name, database_id, connection_id
          - error: Error message
          - owners: List of owner dictionaries
          - notification_message: Pre-formatted notification message

    Example:
        >>> failed = [{"name": "DB1", "database_id": "123", "owners": [{"email": "user@example.com"}]}]
        >>> notification_data = prepare_notification_data(failed)
        >>> # Use notification_data for sending notifications
        >>> # Or serialize to JSON: json.dumps(notification_data, indent=2)
    """
    # Structure the data for notifications
    notification_data = {
        "generated_at": datetime.now().isoformat(),
        "total_failed": len(failed_databases),
        "failed_databases": [
            {
                "database": {
                    "name": db.get("name", "Unknown"),
                    "database_id": db.get("database_id"),
                    "connection_id": db.get("connection_id"),
                },
                "error": db.get("error", "Unknown error"),
                "owners": db.get("owners", []),  # Array of owners
                "notification_message": db.get("notification_message"),  # Pre-formatted message
            }
            for db in failed_databases
        ],
    }

    return notification_data


def get_database_owners_info(
    client: CollibraClient,
    db_manager: DatabaseConnectionManager,
    database_id: str,
) -> List[Dict[str, Any]]:
    """
    Get all database asset owner information from Catalog Database API.
    
    Cataloged databases can have one or several owners in the ownerIds array.
    This function fetches information for ALL owners.
    
    Args:
        client: CollibraClient instance.
        db_manager: DatabaseConnectionManager instance.
        database_id: UUID of the database asset.
        
    Returns:
        List of dictionaries, each containing owner information with keys:
        - owner_id: Owner user ID
        - email: Owner email address (may be None)
        - username: Owner username (may be None)
        - name: Owner full name (may be None)
        Returns empty list if no owners found or error occurs.
    """
    owners = []
    
    try:
        # Get database asset from Catalog Database API
        # Cataloged databases always have one or several owners in ownerIds array
        db_asset = db_manager.get_database_asset(database_id)
        
        # Catalog Database API returns ownerIds as an array (per API documentation)
        owner_ids = db_asset.get("ownerIds")
        
        if not owner_ids or not isinstance(owner_ids, list) or len(owner_ids) == 0:
            return owners
        
        # Fetch information for ALL owners
        for owner_id in owner_ids:
            try:
                user = client.get_user(owner_id)
                owners.append({
                    "owner_id": owner_id,
                    "email": user.get("email") or user.get("emailAddress"),
                    "username": user.get("username"),
                    "name": (
                        f"{user.get('firstName', '')} {user.get('lastName', '')}".strip() 
                        or user.get("fullName") 
                        or user.get("username")
                    ),
                })
            except Exception as e:
                # If we can't fetch user details, still include the owner ID
                owners.append({
                    "owner_id": owner_id,
                    "email": None,
                    "username": None,
                    "name": None,
                })
            
    except Exception as e:
        # Return empty list on error
        return owners
    
    return owners


def format_notification_message(
    database_name: str,
    database_id: str,
    connection_id: Optional[str],
    error_message: str,
    owners: List[Dict[str, Any]],
) -> str:
    """
    Format a human-readable notification message for database synchronization failures.
    
    This function creates a friendly, informative message that can be sent to
    database owners to notify them about synchronization failures.
    
    Args:
        database_name: Name of the database that failed.
        database_id: UUID of the database asset.
        connection_id: UUID of the database connection (optional).
        error_message: Error message from the synchronization failure.
        owners: List of owner dictionaries with owner_id, email, username, name.
        
    Returns:
        Formatted string message ready for notification (email, Slack, etc.).
        
    Example:
        >>> owners = [{"name": "John Doe", "email": "john@example.com"}]
        >>> msg = format_notification_message("MyDB", "123", "456", "Connection failed", owners)
        >>> print(msg)
    """
    # Start with a friendly greeting
    message_parts = [
        "Hello,",
        "",
        "We wanted to inform you that the metadata synchronization for your database has failed.",
        "",
    ]
    
    # Database information
    message_parts.extend([
        f"Database: {database_name}",
        f"Database ID: {database_id}",
    ])
    
    if connection_id:
        message_parts.append(f"Connection ID: {connection_id}")
    
    message_parts.append("")
    
    # Error information
    message_parts.extend([
        "Error Details:",
        f"  {error_message}",
        "",
    ])
    
    # Owner information (if available)
    if owners:
        if len(owners) == 1:
            owner = owners[0]
            owner_name = owner.get("name") or owner.get("email") or owner.get("username") or "Database Owner"
            message_parts.extend([
                f"This notification is being sent to you as the owner of this database.",
                f"Owner: {owner_name}",
                "",
            ])
        else:
            message_parts.extend([
                f"This notification is being sent to all {len(owners)} owners of this database:",
                "",
            ])
            for idx, owner in enumerate(owners, 1):
                owner_name = owner.get("name") or owner.get("email") or owner.get("username") or f"Owner {idx}"
                owner_email = owner.get("email")
                owner_info = f"  {idx}. {owner_name}"
                if owner_email:
                    owner_info += f" ({owner_email})"
                message_parts.append(owner_info)
            message_parts.append("")
    
    # Action items
    message_parts.extend([
        "Please review the database connection settings and credentials to resolve this issue.",
        "",
        "If you need assistance, please contact your Collibra administrator.",
        "",
        "Best regards,",
        "Collibra Database Synchronization System",
    ])
    
    return "\n".join(message_parts)


def monitor_job_status(
    client: CollibraClient,
    job_id: str,
    max_attempts: int = 10,
    delay_seconds: int = 5,
) -> Dict[str, Any]:
    """
    Monitor job status until completion or failure.
    
    Returns:
        Dictionary with job status information.
    """
    for attempt in range(max_attempts):
        try:
            job_status = client.get_job_status(job_id)
            
            # Try to extract status from various possible fields
            status = (
                job_status.get("status") or
                job_status.get("state") or
                job_status.get("jobStatus") or
                job_status.get("currentStatus") or
                "UNKNOWN"
            )
            status_upper = str(status).upper()
            
            # Try to extract progress
            progress = (
                job_status.get("progress") or
                job_status.get("progressPercentage") or
                job_status.get("completionPercentage") or
                0
            )
            
            # Try to extract message
            message_raw = (
                job_status.get("message") or
                job_status.get("statusMessage") or
                ""
            )
            
            if status_upper in ["COMPLETED", "SUCCESS", "DONE", "FINISHED"]:
                return {
                    "status": "completed",
                    "progress": progress,
                    "message": message_raw,
                }
            elif status_upper in ["FAILED", "ERROR", "CANCELLED", "CANCELED"]:
                error_msg = (
                    job_status.get("error") or
                    job_status.get("errorMessage") or
                    message_raw or
                    "Unknown error"
                )
                return {
                    "status": "failed",
                    "progress": progress,
                    "message": error_msg,
                    "error": error_msg,
                }
            else:
                # Still in progress
                if attempt < max_attempts - 1:
                    time.sleep(delay_seconds)
                    
        except Exception as e:
            if attempt < max_attempts - 1:
                time.sleep(delay_seconds)
            else:
                return {
                    "status": "error",
                    "message": f"Error monitoring job: {e}",
                }
    
    return {
        "status": "timeout",
        "message": f"Job did not complete within {max_attempts * delay_seconds} seconds",
    }


def main():
    """Main orchestrator function."""
    print("=" * 80)
    print("COLLIBRA DATABASE CONNECTION TESTING - MAIN ORCHESTRATOR")
    print("=" * 80)
    print()

    try:
        # Step 1: Load configuration
        print("STEP 1: Loading configuration...")
        config = CollibraConfig.from_env()
        print(f"   ✓ Base URL: {config.base_url}")
        print(f"   ✓ Client ID: {config.client_id[:20]}...")
        print()

        # Step 2: Create client
        print("STEP 2: Creating Collibra client...")
        client = CollibraClient(
            base_url=config.base_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
            timeout=config.timeout,
        )
        print("   ✓ Client created")
        print()

        # Step 3: Test OAuth connection
        print("STEP 3: Testing OAuth connection...")
        try:
            connection_result = client.test_connection()
            if connection_result:
                print("   ✓ OAuth connection successful")
            else:
                print("   ✗ OAuth connection failed")
                return 1
        except Exception as e:
            if "429" in str(e) or "Rate limit" in str(e):
                print("   ⚠ Rate limit hit - waiting 30 seconds...")
                time.sleep(30)
                try:
                    connection_result = client.test_connection()
                    if connection_result:
                        print("   ✓ OAuth connection successful after retry")
                    else:
                        print("   ✗ OAuth connection failed after retry")
                        return 1
                except Exception as retry_e:
                    print(f"   ✗ OAuth connection failed: {retry_e}")
                    return 1
            else:
                print(f"   ✗ OAuth connection failed: {e}")
                return 1
        print()

        # Step 4: Create database manager
        print("STEP 4: Creating database connection manager...")
        db_manager = DatabaseConnectionManager(
            client=client,
            use_oauth=True,
        )
        print("   ✓ Database manager created")
        print()

        # Step 5: List database connections
        print("STEP 5: Fetching database connections...")
        try:
            all_connections = db_manager.list_database_connections()
            # Filter to connections with both edge_connection_id and database_id
            connections = [
                conn for conn in all_connections
                if conn.edge_connection_id and conn.database_id
            ]
            print(f"   ✓ Found {len(all_connections)} total connections")
            print(f"   ✓ Found {len(connections)} connections with both edge and database IDs")
        except Exception as e:
            print(f"   ✗ Failed to fetch connections: {e}")
            return 1
        print()

        if not connections:
            print("   ⚠ No database connections found with both edge_connection_id and database_id")
            return 0

        # Step 6: Process each connection
        print("=" * 80)
        print("STEP 6: Processing database connections")
        print("=" * 80)
        print()

        successful = []
        failed = []

        for i, connection in enumerate(connections, 1):
            print(f"[{i}/{len(connections)}] Processing: {connection.name}")
            print(f"   Connection ID: {connection.id}")
            print(f"   Database ID: {connection.database_id}")
            
            try:
                # Synchronize metadata
                print(f"   Triggering metadata synchronization...")
                sync_result = db_manager.synchronize_database_metadata(connection.database_id)
                
                job_id = sync_result.get("jobId") or sync_result.get("id")
                if not job_id:
                    print(f"   ⚠ No job ID returned")
                    successful.append({
                        "name": connection.name,
                        "database_id": connection.database_id,
                        "status": "no_job_id",
                    })
                    print()
                    continue
                
                print(f"   Job ID: {job_id}")
                print(f"   Monitoring job status...")
                
                # Monitor job
                job_result = monitor_job_status(client, job_id, max_attempts=10, delay_seconds=5)
                
                if job_result["status"] == "failed":
                    print(f"   ✗ Synchronization FAILED")
                    print(f"   Error: {job_result.get('error', job_result.get('message', 'Unknown error'))}")
                    
                    # Fetch owner information (can be multiple owners)
                    print(f"   Fetching database asset owner information...")
                    owners_info = get_database_owners_info(
                        client, db_manager, connection.database_id
                    )
                    
                    if owners_info:
                        print(f"   ✓ Owner Information ({len(owners_info)} owner(s)):")
                        for idx, owner in enumerate(owners_info, 1):
                            print(f"      Owner {idx}:")
                            print(f"         - Owner ID: {owner.get('owner_id', 'N/A')}")
                            if owner.get("name"):
                                print(f"         - Name: {owner.get('name')}")
                            if owner.get("email"):
                                print(f"         - Email: {owner.get('email')}")
                            if owner.get("username"):
                                print(f"         - Username: {owner.get('username')}")
                    else:
                        print(f"   ⚠ Could not retrieve owner information")
                    
                    # Format notification message
                    notification_msg = format_notification_message(
                        database_name=connection.name,
                        database_id=connection.database_id,
                        connection_id=connection.id,
                        error_message=job_result.get("error", job_result.get("message", "Unknown error")),
                        owners=owners_info or [],
                    )
                    
                    failed.append({
                        "name": connection.name,
                        "database_id": connection.database_id,
                        "connection_id": connection.id,
                        "error": job_result.get("error", job_result.get("message", "Unknown error")),
                        "owners": owners_info or [],
                        "notification_message": notification_msg,
                    })
                elif job_result["status"] == "completed":
                    print(f"   ✓ Synchronization completed successfully")
                    successful.append({
                        "name": connection.name,
                        "database_id": connection.database_id,
                    })
                else:
                    print(f"   ⚠ Job status: {job_result.get('status')} - {job_result.get('message', 'Unknown')}")
                    successful.append({
                        "name": connection.name,
                        "database_id": connection.database_id,
                        "status": job_result.get("status"),
                    })
                    
            except Exception as e:
                print(f"   ✗ Error during synchronization: {e}")
                
                # Fetch owner information even when synchronization request fails (can be multiple owners)
                print(f"   Fetching database asset owner information...")
                owners_info = get_database_owners_info(
                    client, db_manager, connection.database_id
                )
                
                if owners_info:
                    print(f"   ✓ Owner Information ({len(owners_info)} owner(s)):")
                    for idx, owner in enumerate(owners_info, 1):
                        print(f"      Owner {idx}:")
                        print(f"         - Owner ID: {owner.get('owner_id', 'N/A')}")
                        if owner.get("name"):
                            print(f"         - Name: {owner.get('name')}")
                        if owner.get("email"):
                            print(f"         - Email: {owner.get('email')}")
                        if owner.get("username"):
                            print(f"         - Username: {owner.get('username')}")
                else:
                    print(f"   ⚠ Could not retrieve owner information")
                
                # Format notification message
                notification_msg = format_notification_message(
                    database_name=connection.name,
                    database_id=connection.database_id,
                    connection_id=connection.id,
                    error_message=str(e),
                    owners=owners_info or [],
                )
                
                failed.append({
                    "name": connection.name,
                    "database_id": connection.database_id,
                    "connection_id": connection.id,
                    "error": str(e),
                    "owners": owners_info or [],
                    "notification_message": notification_msg,
                })
            
            print()

        # Step 7: Display comprehensive summary
        print("=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80)
        print()
        print(f"Total databases processed: {len(connections)}")
        print(f"Successful synchronizations: {len(successful)}")
        print(f"Failed synchronizations: {len(failed)}")
        print()

        if failed:
            print("=" * 80)
            print("FAILED DATABASES AND THEIR OWNERS")
            print("=" * 80)
            print()
            for db in failed:
                print(f"Database: {db['name']}")
                print(f"  Database ID: {db['database_id']}")
                print(f"  Connection ID: {db.get('connection_id', 'N/A')}")
                print(f"  Error: {db['error']}")
                
                owners = db.get('owners', [])
                if owners:
                    print(f"  Owners ({len(owners)}):")
                    for idx, owner in enumerate(owners, 1):
                        print(f"    Owner {idx}:")
                        if owner.get('name'):
                            print(f"      - Name: {owner['name']}")
                        if owner.get('email'):
                            print(f"      - Email: {owner['email']}")
                        if owner.get('username'):
                            print(f"      - Username: {owner['username']}")
                        print(f"      - Owner ID: {owner.get('owner_id', 'N/A')}")
                else:
                    print(f"  Owners: ⚠ Could not retrieve owner information")
                
                # Display notification message preview
                if db.get('notification_message'):
                    print(f"\n  Notification Message Preview:")
                    message_lines = db['notification_message'].split('\n')
                    preview_lines = message_lines[:5]
                    for line in preview_lines:
                        print(f"    {line}")
                    if len(message_lines) > 5:
                        remaining_lines = len(message_lines) - 5
                        print(f"    ... ({remaining_lines} more lines)")
                
                print()
        else:
            print("✓ No failed synchronizations - all databases synchronized successfully!")
            print()

        if successful:
            print("=" * 80)
            print("SUCCESSFUL DATABASES")
            print("=" * 80)
            for db in successful:
                print(f"  ✓ {db['name']}")
            print()

        # Step 8: Prepare notification data
        notification_data = None
        if failed:
            print("=" * 80)
            print("STEP 8: Preparing notification data")
            print("=" * 80)
            print()
            try:
                notification_data = prepare_notification_data(failed)
                print(f"   ✓ Notification data prepared")
                print(f"   ✓ Contains {len(failed)} failed database(s) with owner information")
                print(f"   ✓ Data structure ready for notifications (stored in variable)")
                print()
                print("   Example JSON structure:")
                example_structure = {
                    "generated_at": notification_data["generated_at"],
                    "total_failed": notification_data["total_failed"],
                    "failed_databases": [
                        {
                            "database": {"name": db["database"]["name"]},
                            "error": db["error"][:50] + "..." if len(db["error"]) > 50 else db["error"],
                            "owners_count": len(db["owners"]),
                        }
                        for db in notification_data["failed_databases"][:1]
                    ],
                }
                print("   " + json.dumps(example_structure, indent=6))
                print()
            except Exception as e:
                print(f"   ✗ Failed to prepare notification data: {e}")
                print()
        else:
            print("=" * 80)
            print("STEP 8: No failed databases - no notification data to prepare")
            print("=" * 80)
            print()

        print("=" * 80)
        print("PROCESS COMPLETED")
        print("=" * 80)
        print()
        
        # Notification data is available in the 'notification_data' variable
        # Use it for sending notifications (email, Slack, etc.)
        if notification_data:
            print("💡 Notification data is stored and ready to use.")
            print(f"   Access it via: notification_data variable")
            print(f"   Total failed databases: {notification_data['total_failed']}")
            print()

        return 0 if len(failed) == 0 else 1

    except ValueError as e:
        print(f"✗ Configuration error: {e}")
        print("\nPlease ensure your .env file contains:")
        print("  - COLLIBRA_BASE_URL")
        print("  - COLLIBRA_CLIENT_ID")
        print("  - COLLIBRA_CLIENT_SECRET")
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

