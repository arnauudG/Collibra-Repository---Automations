"""
Simple connection test script.

This script tests the OAuth connection to Collibra without requiring
database connection testing. Useful for quick validation.
"""

import sys
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from collibra_client import CollibraClient, CollibraConfig
except ImportError as e:
    print(f"Error importing collibra_client: {e}")
    print("\nMake sure dependencies are installed:")
    print("  pip install requests python-dotenv")
    print("  or")
    print("  uv sync")
    sys.exit(1)


def test_oauth_connection():
    """Test OAuth connection to Collibra."""
    print("=" * 60)
    print("COLLIBRA OAUTH CONNECTION TEST")
    print("=" * 60)
    print()

    try:
        # Load configuration
        print("Loading configuration from environment variables...")
        config = CollibraConfig.from_env()
        print(f"✓ Base URL: {config.base_url}")
        print(f"✓ Client ID: {config.client_id[:10]}..." if config.client_id else "✗ Client ID: Not set")
        print()

        # Create client
        print("Creating Collibra client...")
        client = CollibraClient(
            base_url=config.base_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
            timeout=config.timeout,
        )
        print("✓ Client created")
        print()

        # Test connection
        print("Testing OAuth connection...")
        if client.test_connection():
            print("✓ Connection successful!")
            print()

            # Try to get current user
            print("Fetching current user information...")
            try:
                current_user = client.get("/rest/2.0/users/current")
                # Try multiple fields for username/name
                username = (
                    current_user.get("username") or
                    current_user.get("name") or
                    current_user.get("fullName") or
                    current_user.get("emailAddress") or
                    "Unknown"
                )
                user_id = current_user.get("id", "N/A")
                email = current_user.get("emailAddress", "N/A")
                
                print(f"✓ Current user: {username}")
                print(f"✓ User ID: {user_id}")
                if email != "N/A":
                    print(f"✓ Email: {email}")
                
                # Show available fields for debugging
                if username == "Unknown":
                    print(f"\n⚠ Note: Username not found. Available fields: {list(current_user.keys())[:5]}")
            except Exception as e:
                print(f"⚠ Could not fetch user info: {e}")

            print()
            print("=" * 60)
            print("✓ ALL TESTS PASSED")
            print("=" * 60)
            return True
        else:
            print("✗ Connection failed")
            return False

    except ValueError as e:
        print(f"\n✗ Configuration error: {e}")
        print("\nPlease ensure the following environment variables are set:")
        print("  - COLLIBRA_BASE_URL")
        print("  - COLLIBRA_CLIENT_ID")
        print("  - COLLIBRA_CLIENT_SECRET")
        print("\nOr create a .env file with these values.")
        return False

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_oauth_connection()
    sys.exit(0 if success else 1)

