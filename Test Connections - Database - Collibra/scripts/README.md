# Utility Scripts

This directory contains utility scripts for manual testing and examples. These are **not** pytest tests but can be useful for quick testing and demonstrations.

## Main Orchestrator Script

**Note**: For the complete end-to-end workflow, use the main orchestrator script in the project root:

```bash
python3 main.py
```

This script orchestrates everything from connection testing to sending notifications to owners. See the main `README.md` for details.

## Utility Scripts

The following scripts provide more granular functionality:

### `test_connection_simple.py`
Quick OAuth connection test script.

**Usage:**
```bash
python3 scripts/test_connection_simple.py
```

**What it tests:**
- Loads configuration from `.env`
- Creates authenticated Collibra client
- Tests OAuth connection
- Fetches current user information

### `test_fetch_users.py`
Test script to fetch users from Collibra API.

**Usage:**
```bash
python3 scripts/test_fetch_users.py
```

**What it tests:**
- Loads configuration from `.env`
- Creates authenticated Collibra client
- Tests connection (with rate limit handling)
- Fetches current user information
- Fetches list of users (with pagination)
- Displays user details (ID, email, etc.)

**Features:**
- Handles rate limits gracefully (waits and retries)
- Shows detailed user information
- Demonstrates pagination with limit/offset

### `test_database_connections_simple.py`
Simple script to list database connections.

**Usage:**
```bash
python3 scripts/test_database_connections_simple.py
```

**What it does:**
- Lists all database connections
- Filters to connections with both edge connection ID and database asset ID
- Displays connection details

### `test_database_connections.py`
Full database connection testing script with synchronization and notifications.

**Usage:**
```bash
python3 scripts/test_database_connections.py
```

**What it does:**
- Tests OAuth connection
- Lists all database connections
- Tests each connection
- Synchronizes metadata for each database
- Monitors job status
- Fetches owner information for failures
- Provides detailed summary report

### `test_synchronize_database.py`
Standalone script for database metadata synchronization.

**Usage:**
```bash
python3 scripts/test_synchronize_database.py
```

**What it does:**
- Fetches database connections with both edge connection ID and database asset ID
- Synchronizes metadata for each database asset
- Monitors job status until completion
- Fetches owner information for failed synchronizations
- Provides summary report

### `test_fetch_failing_database_owners.py`
Script to fetch owners for databases that fail synchronization.

**Usage:**
```bash
python3 scripts/test_fetch_failing_database_owners.py
```

**What it does:**
- Lists all database connections with both edge and database IDs
- Attempts to synchronize metadata for each database
- Monitors job status until completion
- For failed synchronizations, fetches and displays owner information
- Uses Catalog Database API which returns `ownerIds` (array)
- Shows summary of failed databases with their owners

**Features:**
- Fetches owner information from `ownerIds` array (Catalog Database API)
- Displays owner name, email, username, and owner ID
- Handles both synchronization failures and job failures
- Provides detailed summary report

### `test_job_status.py`
Utility to inspect job status response structure.

**Usage:**
```bash
python3 scripts/test_job_status.py <job_id>
```

**Example:**
```bash
python3 scripts/test_job_status.py 019c41d0-b593-74a4-a236-4a80e21765c3
```

**What it does:**
- Fetches job status for a given job ID
- Displays full response structure
- Shows extracted fields for debugging

## Requirements

All scripts require:
- `.env` file with Collibra credentials
- Python dependencies installed (`uv sync` or `pip install -e ".[dev]"`)

## Note

For formal testing, use pytest tests in the `tests/` directory:
```bash
# Run integration tests
uv run pytest -m integration -v

# Run without coverage (recommended to avoid INTERNALERROR)
uv run pytest -m integration -v --no-cov

# Run specific test
uv run pytest tests/test_connection.py::TestConnection::test_connection_success -v
```

**Rate Limiting**: If you encounter rate limits (429 errors) when running pytest tests, they will automatically skip instead of failing. To avoid rate limits:
- Run tests individually
- Wait between test runs
- Use these utility scripts for quick checks instead of pytest

See the main `README.md` for comprehensive testing documentation.

