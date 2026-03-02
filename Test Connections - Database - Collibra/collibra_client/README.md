# Collibra client SDK

`collibra_client` is a small Python SDK used by the controls in `governance_controls/`.
It focuses on the operations those controls need:

- authenticate (OAuth2 client credentials or Basic Auth)
- call REST endpoints (including Collibra REST v2)
- call Edge GraphQL
- poll async jobs
- retry transient failures (rate limits / 5xx)

This is not intended to be a full “everything Collibra” wrapper. It’s the minimum surface
area to run governance automations reliably.

## Install

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Configure

Set credentials via `.env` (see the root `.env.example`):

```bash
COLLIBRA_BASE_URL=https://your-instance.collibra.com
COLLIBRA_CLIENT_ID=your_client_id
COLLIBRA_CLIENT_SECRET=your_client_secret

# Optional alternative:
# COLLIBRA_USERNAME=your_username
# COLLIBRA_PASSWORD=your_password
```

## Quick start

### Authentication Methods

The SDK supports two authentication methods. OAuth 2.0 is recommended for governance automation (unattended, scheduled, revocable).

**Method 1: OAuth 2.0 (Recommended for automation)**
```python
from collibra_client import CollibraClient

client = CollibraClient(
    base_url="https://instance.collibra.com",
    client_id="your_client_id",
    client_secret="your_client_secret"
)
```

**Method 2: Basic Authentication (Username/Password)**
```python
from collibra_client import CollibraClient

client = CollibraClient(
    base_url="https://instance.collibra.com",
    username="your_username",
    password="your_password"
)
```

**Method 3: From Environment Variables (Auto-detects)**
```python
from collibra_client import CollibraClient, CollibraConfig

# Loads either OAuth or Basic Auth from .env
config = CollibraConfig.from_env()

client = CollibraClient(
    base_url=config.base_url,
    client_id=config.client_id,
    client_secret=config.client_secret,
    username=config.username,
    password=config.password
)
```

### Validate connectivity

```python
from collibra_client import DatabaseConnectionManager

# Verify the SDK can reach your Collibra instance
if client.test_connection():
    print("Connected successfully!")

# Confirm identity — useful for auditing which service account runs governance controls
user = client.get("/rest/2.0/users/current")
print(f"Logged in as: {user.get('username')}")

# Query governed database connections
db_manager = DatabaseConnectionManager(client=client)
connections = db_manager.list_database_connections()

for conn in connections:
    print(f"{conn.name} (ID: {conn.id})")
```

## Where things live

### `core/` — Governance Infrastructure
Core functionality that every governance operation depends on:
- `auth.py`: OAuth 2.0 authenticator with thread-safe token caching and automatic refresh
- `client.py`: Resilient HTTP client with retry logic, GraphQL support, and job polling
- `config.py`: Environment-based configuration management (loads from `.env`)
- `exceptions.py`: Governance exception hierarchy for actionable error handling

### `catalog/` — Data Source Governance
Operations for validating and managing the data sources Collibra governs:
- `connections.py`: Database connection manager for the Catalog Database API
- Support for both OAuth Bearer tokens and Basic Authentication
- Connection listing, refresh, testing, and metadata synchronization

## Common patterns

### Validate data source connectivity

The most fundamental governance operation: can Collibra still reach the data sources it's supposed to govern?

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

### Manage governed database connections

Query, refresh, and test the database connections under governance:

```python
from collibra_client import DatabaseConnectionManager

# Create database manager (uses OAuth by default)
db_manager = DatabaseConnectionManager(client=client, use_oauth=True)

# List all database connections under governance
connections = db_manager.list_database_connections()
for conn in connections:
    print(f"{conn.name} (ID: {conn.id})")

# Trigger a metadata refresh for an Edge Site
result = db_manager.refresh_database_connections(
    edge_connection_id="your-edge-id"
)
print(f"Refresh job started: {result.get('id')}")

# Test a specific connection's reachability
job_id = db_manager.test_edge_connection(edge_connection_id="your-edge-id")
job_status = client.get_edge_job_status(job_id)
print(f"Test status: {job_status.get('status')}")
```

### Query Edge Site topology via GraphQL

Governance controls need to understand the topology of Edge Sites — which connections belong to which sites, and what their current state is:

```python
# Query Edge Site connections
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

### Handle failures explicitly

Governance controls must distinguish between different failure modes — an expired credential is a different remediation path than a network timeout:

```python
from collibra_client.core.exceptions import CollibraAPIError, CollibraAuthenticationError

try:
    data = client.get("/rest/2.0/assets")
except CollibraAuthenticationError as e:
    # Credential issue — the governance service account may need rotation
    print(f"Authentication failed: {e}")
except CollibraAPIError as e:
    # Infrastructure issue — Collibra may be down or rate-limiting
    print(f"API error: {e.status_code}")
    print(f"Details: {e.response_body}")
```

## Testing

The SDK includes integration tests that validate governance operations against a live Collibra instance:

```bash
# Run all SDK tests
uv run pytest tests/integration/core tests/integration/catalog

# Run specific test module
uv run pytest tests/integration/catalog/test_database_connections.py

# Run with verbose output
uv run pytest tests/integration/ -v
```

**Note**: Integration tests require valid Collibra credentials in your `.env` file.

## Resilience for Governance Operations

Governance controls run on schedules, often unattended. They cannot fail silently due to transient infrastructure issues. The SDK provides several layers of resilience.

### Token Caching

OAuth tokens are cached in `~/.collibra/token_cache/` with session-specific names. This prevents unnecessary token requests across control executions and eliminates redundant authentication round-trips during long-running governance runs.

### Automatic Retry Strategy

The client automatically retries failed requests so that momentary Collibra outages or rate limits don't cause governance controls to report false failures:
- **Status codes**: 429 (rate limit), 500, 502, 503, 504
- **Retry count**: 3 attempts
- **Backoff**: Exponential backoff with 1-second base

### Job Polling for Asynchronous Operations

Many governance operations (refresh, test, sync) are asynchronous. The SDK provides a polling pattern to track them to completion:

```python
# Start an async governance operation
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
