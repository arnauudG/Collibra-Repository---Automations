# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A unified Collibra governance automation platform with a two-pillar architecture:
1. **SDK** (`collibra_client`): Production-ready Python library for Collibra API interactions
2. **Governance Controls** (`governance_controls`): Modular framework for automated governance controls

The platform bridges Collibra's cloud governance metadata with on-premise/VPC data infrastructure.

## Development Commands

### Environment Setup
```bash
# Install dependencies (uses uv package manager)
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your Collibra OAuth credentials

# Install pre-commit hooks
pre-commit install
```

### Testing
```bash
# Run all tests
uv run pytest

# Run integration tests only
uv run pytest -m integration

# Run with coverage
uv run pytest --cov=collibra_client --cov-report=term-missing

# Run specific test file
uv run pytest tests/integration/catalog/test_database_connections.py

# Run single test
uv run pytest tests/integration/catalog/test_database_connections.py::TestDatabaseConnections::test_list_database_connections
```

### Code Quality
```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Format code (black)
black . --line-length=100

# Lint (ruff)
ruff check --fix

# Type checking (mypy)
mypy collibra_client --ignore-missing-imports

# Sort imports (isort)
isort . --profile black --line-length=100
```

### Running Governance Controls
```bash
# Execute the Edge Connection Testing control
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py
```

## Architecture

### SDK Layer (`collibra_client`)

**Purpose**: Standalone, reusable library for Collibra API interactions.

**Core Components**:
- `core/auth.py`: OAuth 2.0 token management with automatic refresh and thread-safe caching
- `core/client.py`: HTTP client with retry logic (429, 5xx), supports GET/POST/PUT/DELETE/GraphQL
- `core/config.py`: Environment-based configuration (loads from `.env`)
- `core/exceptions.py`: Exception hierarchy (`CollibraAPIError`, `CollibraAuthenticationError`)

**Catalog Components**:
- `catalog/connections.py`: Database connection manager supporting:
  - Catalog Database Registration API (OAuth Bearer or Basic Auth)
  - Edge GraphQL API for connection testing and job polling
  - Connection listing, refresh, and testing operations

**Key Design Patterns**:
- Dependency injection for authenticator (enables testing)
- Automatic token refresh on 401 responses
- Retry strategy with exponential backoff
- Job polling pattern for async operations (refresh, test, sync jobs)

**API Coverage**:
- REST v2.0: Users (`/rest/2.0/users`), Jobs (`/rest/jobs/v1/jobs`)
- Catalog Database API: `/rest/catalogDatabase/v1/databaseConnections`, `/rest/catalogDatabase/v1/databases`
- Edge GraphQL API: `/edge/api/graphql` for connection testing, job status, and Edge Site queries

### Governance Controls Layer (`governance_controls`)

**Purpose**: Application layer for automated governance controls built on the SDK.

**Current Controls**:
- `test_edge_connections`: Validates database connectivity for governed Edge Sites

**Control Architecture** (`test_edge_connections`):
- `logic/orchestrator.py`: Main workflow coordinator (refresh → poll → test → notify)
- `logic/poller.py`: Job status polling with timeout handling
- `logic/reporter.py`: Generates human-friendly reports and summaries
- `logic/impact_mapper.py`: Maps technical failures to business owners
- `logic/heuristic.py`: Connection health analysis logic
- `notifications/`: Owner notification system (console, email handlers)
- `governed_config.py`: Loads governed Edge Site IDs from `governed_connections.yaml`

**Configuration**:
- `governed_connections.yaml`: Version-controlled list of Edge Site IDs to govern
  - Each entry includes: Edge Site ID, name, description, environment, owner_team
  - These IDs determine which connections are tested and which owners are notified

### Authentication Architecture

**OAuth 2.0 Flow** (Primary):
- Client credentials flow for machine-to-machine authentication
- Token caching in `~/.collibra/token_cache/` with session-specific naming
- Automatic refresh when tokens expire (401 response)
- Thread-safe token management

**Basic Auth** (Fallback):
- Supported by Catalog Database API only
- Use `DatabaseConnectionManager(client, use_oauth=False, username=..., password=...)`
- Default behavior: use OAuth Bearer token from client

### Job Polling Pattern

Many Collibra operations are asynchronous and return job IDs:
- Catalog refresh: `refresh_database_connections()` → 202 response with `jobId`
- Connection testing: `test_edge_connection()` → returns `jobId`
- Metadata sync: `synchronize_database_metadata()` → returns `jobId`

**Polling Implementation**:
1. Submit job and get `job_id`
2. Poll job status using `client.get_job_status(job_id)` or `client.get_edge_job_status(job_id)`
3. Edge jobs require GraphQL polling via `get_edge_job_status()`
4. Handle job states: RUNNING, SUCCESS, FAILED, ERROR
5. Implement timeout and retry logic (see `logic/poller.py`)

## Testing Guidelines

**Integration Tests**:
- Located in `tests/integration/` (mirrors source structure)
- Use pytest markers: `@pytest.mark.integration`, `@pytest.mark.rate_limit`
- Rate limit handling via `@handle_rate_limit` decorator (see `tests/conftest.py`)
- Tests require real Collibra credentials in `.env`

**Fixtures** (in `tests/conftest.py`):
- `collibra_client`: Configured CollibraClient instance
- `db_manager`: DatabaseConnectionManager with OAuth enabled
- Automatic credential loading from `.env`

**Testing Best Practices**:
- Skip tests gracefully if prerequisites missing (`pytest.skip()`)
- Handle rate limiting (429 responses) by catching and skipping
- Use small result sets (`limit=10`) to minimize API calls
- Test edge cases: connections with/without database_id, empty result sets

## Configuration Files

**`.env`** (not committed):
- Required: `COLLIBRA_BASE_URL`, `COLLIBRA_CLIENT_ID`, `COLLIBRA_CLIENT_SECRET`
- Optional: `COLLIBRA_BASIC_AUTH_USERNAME`, `COLLIBRA_BASIC_AUTH_PASSWORD`, `COLLIBRA_TIMEOUT`

**`governed_connections.yaml`** (version-controlled):
- Located in `governance_controls/test_edge_connections/`
- Defines Edge Site IDs to govern (find in URL: `.../settings/edge/sites/<EDGE_SITE_ID>`)
- Each entry maps Edge Site ID → metadata (name, description, environment, owner_team)

**`pyproject.toml`**:
- Build system: hatchling
- Code formatting: black (line-length=100)
- Linting: ruff (pyflakes, pycodestyle, isort, flake8-bugbear)
- Type checking: mypy (check_untyped_defs=true)
- Testing: pytest with coverage

## Code Style

- Line length: 100 characters (enforced by black and ruff)
- Python version: 3.9+ (target: py39, py310, py311, py312)
- Import sorting: isort with black profile
- Type hints: Preferred but not strictly enforced (mypy with `disallow_untyped_defs=false`)
- Docstrings: Google-style docstrings for public APIs

## Common Patterns

### Creating a Collibra Client
```python
from collibra_client import CollibraClient, CollibraConfig

config = CollibraConfig.from_env()
client = CollibraClient(
    base_url=config.base_url,
    client_id=config.client_id,
    client_secret=config.client_secret
)
```

### Managing Database Connections
```python
from collibra_client import DatabaseConnectionManager

# OAuth Bearer token (recommended)
db_manager = DatabaseConnectionManager(client=client, use_oauth=True)

# Refresh connections for a governed Edge Site
result = db_manager.refresh_database_connections(edge_connection_id="edge-uuid")

# List connections
connections = db_manager.list_database_connections(edge_connection_id="edge-uuid")

# Test connection
job_id = db_manager.test_edge_connection(edge_connection_id="edge-uuid")
job_status = client.get_edge_job_status(job_id)
```

### GraphQL Queries
```python
query = """
query ConnectionDetail($connectionId: ID!) {
  connectionById(id: $connectionId) {
    id
    name
    parameters
  }
}
"""
variables = {"connectionId": "conn-uuid"}
response = client.post_graphql(
    endpoint="/edge/api/graphql",
    query=query,
    variables=variables,
    operation_name="ConnectionDetail"
)
data = response["data"]["connectionById"]
```

### Error Handling
```python
from collibra_client.core.exceptions import CollibraAPIError, CollibraAuthenticationError

try:
    result = client.get("/rest/2.0/assets")
except CollibraAuthenticationError as e:
    # Handle auth failures (invalid credentials, expired token)
    logger.error(f"Authentication failed: {e}")
except CollibraAPIError as e:
    # Handle API errors (HTTP errors, network errors)
    logger.error(f"API error: {e.status_code} - {e.response_body}")
```

## Project-Specific Notes

- **Rate Limiting**: Collibra enforces rate limits (429 Too Many Requests). Tests include retry logic and graceful handling.
- **Token Caching**: OAuth tokens cached in `~/.collibra/token_cache/` with session names. Clean cache if switching environments.
- **Edge vs Core APIs**: Edge operations require GraphQL (`/edge/api/graphql`), Core operations use REST v2.0 (`/rest/2.0/`).
- **Job Polling**: Always implement timeout logic for async operations. Default timeout in controls: 60 seconds.
- **Governed Scope**: Only test connections under governed Edge Sites (defined in `governed_connections.yaml`). Don't test all connections indiscriminately.
- **Owner Notifications**: Failed connection tests trigger owner notifications via the notification handler pattern.
