#!/usr/bin/env python3
"""
Simple test script to fetch users from Collibra API.

This script demonstrates:
- Loading configuration from .env
- Creating an authenticated client
- Fetching users from the API
- Displaying user information
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import collibra_client
sys.path.insert(0, str(Path(__file__).parent.parent))

from collibra_client import (
    CollibraClient,
    CollibraConfig,
    CollibraAuthenticationError,
)


def main():
    """Test fetching users from Collibra API."""
    print("=" * 60)
    print("Collibra Client - Fetch Users Test")
    print("=" * 60)
    print()

    try:
        # Load configuration from environment variables
        print("1. Loading configuration from .env...")
        config = CollibraConfig.from_env()
        print(f"   ✓ Base URL: {config.base_url}")
        print(f"   ✓ Client ID: {config.client_id[:10]}...")
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

        # Test connection
        print("3. Testing connection...")
        try:
            connection_result = client.test_connection()
            if connection_result:
                print("   ✓ Connection successful!")
            else:
                print("   ✗ Connection failed")
                return 1
        except CollibraAuthenticationError as e:
            if "429" in str(e) or "Rate limit" in str(e):
                print("   ⚠ Rate limit hit - waiting 30 seconds...")
                import time
                time.sleep(30)
                print("   Retrying connection...")
                try:
                    connection_result = client.test_connection()
                    if connection_result:
                        print("   ✓ Connection successful after retry!")
                    else:
                        print("   ✗ Connection failed after retry")
                        return 1
                except Exception as retry_e:
                    print(f"   ✗ Connection failed after retry: {retry_e}")
                    print("\n   Note: You may need to wait a few minutes before retrying.")
                    return 1
            else:
                print(f"   ✗ Connection failed: {e}")
                return 1
        except Exception as e:
            print(f"   ✗ Connection failed: {e}")
            return 1
        print()

        # Fetch current user
        print("4. Fetching current user...")
        try:
            current_user = client.get("/rest/2.0/users/current")
            print("   ✓ Current user fetched:")
            print(f"      - ID: {current_user.get('id', 'N/A')}")
            print(f"      - Username: {current_user.get('username', 'N/A')}")
            print(f"      - Name: {current_user.get('name', 'N/A')}")
            if 'emailAddress' in current_user:
                print(f"      - Email: {current_user.get('emailAddress', 'N/A')}")
        except Exception as e:
            print(f"   ✗ Failed to fetch current user: {e}")
            return 1
        print()

        # Fetch users list (with limit)
        print("5. Fetching users list (limit: 10)...")
        try:
            users_response = client.get(
                "/rest/2.0/users",
                params={"limit": 10, "offset": 0}
            )
            
            # Collibra API typically returns results in a 'results' field
            if "results" in users_response:
                users = users_response["results"]
                print(f"   ✓ Fetched {len(users)} users:")
                print()
                for i, user in enumerate(users[:5], 1):  # Show first 5
                    print(f"   User {i}:")
                    print(f"      - ID: {user.get('id', 'N/A')}")
                    print(f"      - Username: {user.get('username', 'N/A')}")
                    print(f"      - Name: {user.get('name', 'N/A')}")
                    if 'emailAddress' in user:
                        print(f"      - Email: {user.get('emailAddress', 'N/A')}")
                    print()
                
                if len(users) > 5:
                    print(f"   ... and {len(users) - 5} more users")
            else:
                print(f"   ✓ Response received: {list(users_response.keys())}")
                print(f"   Response structure: {type(users_response)}")
        except Exception as e:
            print(f"   ✗ Failed to fetch users: {e}")
            import traceback
            traceback.print_exc()
            return 1
        print()

        print("=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        return 0

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

