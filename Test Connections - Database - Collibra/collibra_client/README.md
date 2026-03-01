# Collibra Python Client SDK

A production-ready, reusable Python library for interacting with Collibra's REST and GraphQL APIs. This SDK is designed to be standalone and can be extracted for use in other projects or governance automations.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Module Structure](#module-structure)
- [Usage Examples](#usage-examples)
- [Testing](#testing)
- [Configuration](#configuration)
- [Advanced Features](#advanced-features)

## Features

### Authentication
- **OAuth 2.0**: Client credentials flow with automatic token management
- **Token Caching**: Thread-safe token storage with automatic refresh
- **Basic Auth**: Fallback support for Catalog Database API

### API Coverage
- **REST v2.0**: User management, jobs, assets, and core Collibra operations
- **Catalog Database API**: Database registration, connection management, metadata synchronization
- **GraphQL**: Edge site queries, connection testing, and complex data traversal

### Production-Grade Features
- **Error Handling**: Comprehensive exception hierarchy with detailed error messages
- **Retry Logic**: Automatic retries for transient failures (429, 5xx status codes)
- **Type Safety**: Full type hints for modern Python development
- **Logging**: Configurable logging with colored console output

## Installation

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Quick Start

```python
from collibra_client import CollibraClient, CollibraConfig, DatabaseConnectionManager

# 1. Initialize from Environment
config = CollibraConfig.from_env()

# 2. Create the Client
client = CollibraClient(
    base_url=config.base_url,
    client_id=config.client_id,
    client_secret=config.client_secret
)

# 3. Use specialized managers
db_manager = DatabaseConnectionManager(client=client)
connections = db_manager.list_database_connections()

# 4. Or use raw HTTP methods
user_info = client.get("/rest/2.0/users/current")
```

## Module Structure

### `core/`
Core functionality for API interactions:
- `auth.py`: OAuth 2.0 authenticator with token caching
- `client.py`: HTTP client with retry logic and GraphQL support
- `config.py`: Configuration management from environment variables
- `exceptions.py`: Custom exception hierarchy

### `catalog/`
Catalog-specific operations:
- `connections.py`: Database connection manager for Catalog Database API
- Support for both OAuth Bearer tokens and Basic Authentication
- Connection listing, refresh, testing, and metadata synchronization

## Usage Examples

### Basic Connection Test

```python
from collibra_client import CollibraClient, CollibraConfig

# Load configuration from environment
config = CollibraConfig.from_env()

# Create client
client = CollibraClient(
    base_url=config.base_url,
    client_id=config.client_id,
    client_secret=config.client_secret
)

# Test connection
if client.test_connection():
    print("Connected successfully!")

    # Get current user
    user = client.get("/rest/2.0/users/current")
    print(f"Logged in as: {user.get('username')}")
```

### Database Connection Management

```python
from collibra_client import DatabaseConnectionManager

# Create database manager (uses OAuth by default)
db_manager = DatabaseConnectionManager(client=client, use_oauth=True)

# List all database connections
connections = db_manager.list_database_connections()
for conn in connections:
    print(f"{conn.name} (ID: {conn.id})")

# Refresh connections for an Edge Site
result = db_manager.refresh_database_connections(
    edge_connection_id="your-edge-id"
)
print(f"Refresh job started: {result.get('id')}")

# Test a connection
job_id = db_manager.test_edge_connection(edge_connection_id="your-edge-id")
job_status = client.get_edge_job_status(job_id)
print(f"Test status: {job_status.get('status')}")
```

### GraphQL Queries

```python
# Execute GraphQL query
query = """
query GetConnections($siteId: ID!) {
  edgeSiteById(id: $siteId) {
    id
    name
    connections(input: {limit: 10}) {
      edges {
        node {
          id
          name
        }
      }
    }
  }
}
"""

response = client.post_graphql(
    endpoint="/edge/api/graphql",
    query=query,
    variables={"siteId": "your-site-id"},
    operation_name="GetConnections"
)

connections = response["data"]["edgeSiteById"]["connections"]["edges"]
```

### Error Handling

```python
from collibra_client.core.exceptions import CollibraAPIError, CollibraAuthenticationError

try:
    data = client.get("/rest/2.0/assets")
except CollibraAuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Check credentials and try again
except CollibraAPIError as e:
    print(f"API error: {e.status_code}")
    print(f"Details: {e.response_body}")
```

## Testing

The SDK includes comprehensive integration tests:

```bash
# Run all SDK tests
uv run pytest tests/integration/core tests/integration/catalog

# Run specific test module
uv run pytest tests/integration/catalog/test_database_connections.py

# Run with verbose output
uv run pytest tests/integration/ -v
```

**Note**: Integration tests require valid Collibra credentials in your `.env` file.

## Configuration

The SDK uses environment variables for configuration. Create a `.env` file:

```bash
# Required: OAuth 2.0 credentials
COLLIBRA_BASE_URL=https://your-instance.collibra.com
COLLIBRA_CLIENT_ID=your_client_id
COLLIBRA_CLIENT_SECRET=your_client_secret

# Optional: Request timeout (default: 30 seconds)
COLLIBRA_TIMEOUT=30

# Optional: Basic Auth for Catalog API (if not using OAuth)
COLLIBRA_BASIC_AUTH_USERNAME=your_username
COLLIBRA_BASIC_AUTH_PASSWORD=your_password
```

## Advanced Features

### Token Caching

Tokens are automatically cached in `~/.collibra/token_cache/` with session-specific names. This prevents unnecessary token requests and improves performance.

### Retry Strategy

The client automatically retries failed requests:
- **Status codes**: 429 (rate limit), 500, 502, 503, 504
- **Retry count**: 3 attempts
- **Backoff**: Exponential backoff with 1-second base

### Job Polling

For asynchronous operations, use the job polling pattern:

```python
# Start an async operation
result = db_manager.refresh_database_connections(edge_connection_id="edge-id")
job_id = result.get("id")

# Poll for completion
import time
timeout = 60
start_time = time.time()

while time.time() - start_time < timeout:
    status = client.get_job_status(job_id)
    if status.get("state") in ["COMPLETED", "FAILED"]:
        break
    time.sleep(2)
```

For Edge jobs, use `client.get_edge_job_status(job_id)` instead.
