#!/usr/bin/env python3
"""
Script to fetch owners for databases that are failing synchronization.

This script:
1. Lists all database connections
2. Attempts to synchronize metadata for each database
3. Monitors job status
4. For failed synchronizations, fetches and displays owner information
"""

import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collibra_client import (
    CollibraClient,
    CollibraConfig,
    DatabaseConnectionManager,
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
            print(f"      ⚠ No ownerIds found in database asset response")
            return None
        
        # Use the first owner from the array
        owner_id = owner_ids[0]
        
        if len(owner_ids) > 1:
            print(f"      Note: Database has {len(owner_ids)} owners, using first one")
        
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
            print(f"      ⚠ Could not fetch user details for owner {owner_id}: {e}")
            return {
                "owner_id": owner_id,
                "email": None,
                "username": None,
                "name": None,
            }
            
    except Exception as e:
        print(f"      ⚠ Could not fetch database asset details: {e}")
        return None


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
                if attempt == 0:
                    print(f"      Job status: {status} ({progress}%)")
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
    """Main function to fetch owners for failing databases."""
    print("=" * 70)
    print("Fetch Owners for Failing Database Synchronizations")
    print("=" * 70)
    print()

    try:
        # Load configuration
        print("1. Loading configuration...")
        config = CollibraConfig.from_env()
        print(f"   ✓ Configuration loaded")
        print()

        # Create client
        print("2. Creating Collibra client...")
        client = CollibraClient(
            base_url=config.base_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
            timeout=config.timeout,
        )
        print("   ✓ Client created")
        print()

        # Create database manager
        print("3. Creating database connection manager...")
        db_manager = DatabaseConnectionManager(
            client=client,
            use_oauth=True,
        )
        print("   ✓ Database manager created")
        print()

        # List database connections
        print("4. Fetching database connections...")
        try:
            connections = db_manager.list_database_connections()
            # Filter to connections with both edge_connection_id and database_id
            filtered_connections = [
                conn for conn in connections
                if conn.edge_connection_id and conn.database_id
            ]
            print(f"   ✓ Found {len(filtered_connections)} database connections with both edge and database IDs")
        except Exception as e:
            print(f"   ✗ Failed to fetch connections: {e}")
            return 1
        print()

        if not filtered_connections:
            print("   ⚠ No database connections found with both edge_connection_id and database_id")
            return 0

        # Track results
        failed_databases = []
        successful_databases = []

        # Process each connection
        print("5. Testing synchronization and fetching owners for failures...")
        print("-" * 70)
        
        for i, connection in enumerate(filtered_connections, 1):
            print(f"\n[{i}/{len(filtered_connections)}] Database: {connection.name}")
            print(f"   Connection ID: {connection.id}")
            print(f"   Database ID: {connection.database_id}")
            
            try:
                # Synchronize metadata
                print(f"   Triggering metadata synchronization...")
                sync_result = db_manager.synchronize_database_metadata(connection.database_id)
                
                job_id = sync_result.get("jobId") or sync_result.get("id")
                if not job_id:
                    print(f"   ⚠ No job ID returned from synchronization")
                    successful_databases.append({
                        "name": connection.name,
                        "database_id": connection.database_id,
                        "status": "no_job_id",
                    })
                    continue
                
                print(f"   Job ID: {job_id}")
                print(f"   Monitoring job status...")
                
                # Monitor job
                job_result = monitor_job_status(client, job_id, max_attempts=10, delay_seconds=5)
                
                if job_result["status"] == "failed":
                    print(f"   ✗ Synchronization FAILED")
                    print(f"   Error: {job_result.get('error', job_result.get('message', 'Unknown error'))}")
                    
                    # Fetch owner information
                    print(f"   Fetching database asset owner information...")
                    owner_info = get_database_owner_info(
                        client, db_manager, connection.database_id
                    )
                    
                    if owner_info:
                        print(f"   ✓ Owner Information:")
                        print(f"      - Owner ID: {owner_info.get('owner_id', 'N/A')}")
                        if owner_info.get("name"):
                            print(f"      - Name: {owner_info.get('name')}")
                        if owner_info.get("email"):
                            print(f"      - Email: {owner_info.get('email')}")
                        if owner_info.get("username"):
                            print(f"      - Username: {owner_info.get('username')}")
                        
                        failed_databases.append({
                            "name": connection.name,
                            "database_id": connection.database_id,
                            "connection_id": connection.id,
                            "error": job_result.get("error", job_result.get("message", "Unknown error")),
                            "owner": owner_info,
                        })
                    else:
                        print(f"   ⚠ Could not retrieve owner information")
                        failed_databases.append({
                            "name": connection.name,
                            "database_id": connection.database_id,
                            "connection_id": connection.id,
                            "error": job_result.get("error", job_result.get("message", "Unknown error")),
                            "owner": None,
                        })
                elif job_result["status"] == "completed":
                    print(f"   ✓ Synchronization completed successfully")
                    successful_databases.append({
                        "name": connection.name,
                        "database_id": connection.database_id,
                    })
                else:
                    print(f"   ⚠ Job status: {job_result.get('status')} - {job_result.get('message', 'Unknown')}")
                    successful_databases.append({
                        "name": connection.name,
                        "database_id": connection.database_id,
                        "status": job_result.get("status"),
                    })
                    
            except Exception as e:
                print(f"   ✗ Error during synchronization: {e}")
                
                # Fetch owner information even when synchronization fails
                print(f"   Fetching database asset owner information...")
                owner_info = get_database_owner_info(
                    client, db_manager, connection.database_id
                )
                
                if owner_info:
                    print(f"   ✓ Owner Information:")
                    print(f"      - Owner ID: {owner_info.get('owner_id', 'N/A')}")
                    if owner_info.get("name"):
                        print(f"      - Name: {owner_info.get('name')}")
                    if owner_info.get("email"):
                        print(f"      - Email: {owner_info.get('email')}")
                    if owner_info.get("username"):
                        print(f"      - Username: {owner_info.get('username')}")
                else:
                    print(f"   ⚠ Could not retrieve owner information")
                
                failed_databases.append({
                    "name": connection.name,
                    "database_id": connection.database_id,
                    "connection_id": connection.id,
                    "error": str(e),
                    "owner": owner_info,
                })

        # Summary
        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Total databases processed: {len(filtered_connections)}")
        print(f"Successful synchronizations: {len(successful_databases)}")
        print(f"Failed synchronizations: {len(failed_databases)}")
        print()

        if failed_databases:
            print("FAILED DATABASES AND THEIR OWNERS:")
            print("-" * 70)
            for db in failed_databases:
                print(f"\nDatabase: {db['name']}")
                print(f"  Database ID: {db['database_id']}")
                print(f"  Error: {db['error']}")
                if db['owner']:
                    print(f"  Owner:")
                    if db['owner'].get('name'):
                        print(f"    - Name: {db['owner']['name']}")
                    if db['owner'].get('email'):
                        print(f"    - Email: {db['owner']['email']}")
                    if db['owner'].get('username'):
                        print(f"    - Username: {db['owner']['username']}")
                    print(f"    - Owner ID: {db['owner'].get('owner_id', 'N/A')}")
                else:
                    print(f"  Owner: ⚠ Could not retrieve owner information")
        else:
            print("✓ No failed synchronizations - all databases synchronized successfully!")

        return 0

    except ValueError as e:
        print(f"✗ Configuration error: {e}")
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

