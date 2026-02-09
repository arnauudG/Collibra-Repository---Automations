"""
Simple script to test fetching database connection IDs from Collibra.

This script tests the Catalog Database Registration API to list
all database connections.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from collibra_client import (
        CollibraClient,
        CollibraConfig,
        DatabaseConnectionManager,
    )
except ImportError as e:
    print(f"Error importing collibra_client: {e}")
    print("\nMake sure dependencies are installed:")
    print("  pip install requests python-dotenv")
    sys.exit(1)


def test_list_database_connections():
    """Test listing database connections."""
    print("=" * 60)
    print("DATABASE CONNECTION ID FETCHING TEST")
    print("=" * 60)
    print()

    try:
        # Load configuration
        print("Loading configuration from environment variables...")
        config = CollibraConfig.from_env()
        print(f"✓ Base URL: {config.base_url}")
        print(f"✓ Client ID: {config.client_id[:20]}..." if config.client_id else "✗ Client ID: Not set")
        
        # Create OAuth client
        print("Creating Collibra OAuth client...")
        client = CollibraClient(
            base_url=config.base_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
            timeout=config.timeout,
        )
        print("✓ OAuth client created")
        
        # Test OAuth connection first
        print("\nTesting OAuth connection...")
        if not client.test_connection():
            print("✗ OAuth connection failed")
            return False
        print("✓ OAuth connection successful")
        print()

        # Create database connection manager (using OAuth token)
        print("Creating database connection manager...")
        print("  Using OAuth Bearer token for authentication")
        db_manager = DatabaseConnectionManager(
            client=client,
            use_oauth=True,  # Use OAuth token instead of Basic Auth
        )
        print("✓ Database manager created")
        print()

        # Refresh database connections first to synchronize all connections from data source
        print("Refreshing database connections to synchronize with data source...")
        print("-" * 60)
        
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
        
        # List database connections (now includes all synchronized connections after refresh)
        print("Fetching all database connections...")
        print("-" * 60)
        try:
            all_connections = db_manager.list_database_connections()
            
            # Filter to only connections with both edge connection ID and database asset ID
            connections = [conn for conn in all_connections if conn.database_id is not None]
            
            print(f"\n✓ Successfully fetched {len(all_connections)} total database connection(s)")
            print(f"✓ Filtered to {len(connections)} connection(s) with both edge connection ID and database asset ID\n")
            
            if len(connections) == 0:
                print("⚠ No database connections found with both edge connection ID and database asset ID.")
                print("This could mean:")
                print("  - No connections have been linked to Database assets yet")
                print("  - Connections need to be synchronized and linked in Collibra")
                print("  - Check your Collibra instance for database connections")
            else:
                print("Database Connections (with Edge Connection ID and Database Asset ID):")
                print("=" * 60)
                for i, conn in enumerate(connections, 1):
                    print(f"\n{i}. Connection Name: {conn.name}")
                    print(f"   Connection ID: {conn.id}")
                    print(f"   Edge Connection ID: {conn.edge_connection_id}")
                    print(f"   Database Asset ID: {conn.database_id}")
                print("\n" + "=" * 60)
                
                # Summary
                print(f"\nSummary:")
                print(f"  Total connections fetched: {len(all_connections)}")
                print(f"  Connections with both edge connection ID and database asset ID: {len(connections)}")

            print()
            print("=" * 60)
            print("✓ TEST COMPLETED SUCCESSFULLY")
            print("=" * 60)
            return True

        except Exception as e:
            error_msg = str(e)
            print(f"\n✗ Error fetching database connections: {error_msg}")
            
            # Provide helpful error messages
            if "401" in error_msg or "Unauthorized" in error_msg:
                print("\n⚠ Authentication failed (401 Unauthorized)")
                print("This usually means:")
                print("  1. Basic Auth credentials are incorrect")
                print("  2. The username/password don't have access to Catalog Database API")
                print("  3. Credentials need to be updated in your .env file")
                print("\nPlease verify your COLLIBRA_BASIC_AUTH_USERNAME and COLLIBRA_BASIC_AUTH_PASSWORD")
            elif "403" in error_msg or "Forbidden" in error_msg:
                print("\n⚠ Access denied (403 Forbidden)")
                print("Your credentials are valid but don't have permission to access")
                print("the Catalog Database Registration API.")
            else:
                import traceback
                traceback.print_exc()
            return False

    except ValueError as e:
        print(f"\n✗ Configuration error: {e}")
        print("\nPlease ensure the following environment variables are set:")
        print("  - COLLIBRA_BASE_URL")
        print("  - COLLIBRA_CLIENT_ID")
        print("  - COLLIBRA_CLIENT_SECRET")
        print("  - COLLIBRA_BASIC_AUTH_USERNAME")
        print("  - COLLIBRA_BASIC_AUTH_PASSWORD")
        return False

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_list_database_connections()
    sys.exit(0 if success else 1)

