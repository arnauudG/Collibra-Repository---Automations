# Edge Connection Validation Control

This control validates the connectivity of data sources registered in Collibra Edge Sites. It automatically tests connections, monitors job status, and notifies owners when failures occur.

## Table of Contents

- [Overview](#overview)
- [Business Value](#business-value)
- [How it Works: The Governance Control Loop](#how-it-works-the-governance-control-loop)
- [Architecture](#architecture)
- [Usage](#usage)
- [Testing](#testing)
- [Utility Scripts](#utility-scripts)
- [Notification System](#notification-system)
- [Configuration Options](#configuration-options)
- [Troubleshooting](#troubleshooting)
- [Key Features](#key-features)

## Overview

In enterprise Collibra environments, data source connectivity can break silently due to credential expiration, network changes, or infrastructure updates. This control provides proactive validation:

- **Automated Testing**: Programmatically verifies connectivity on demand or on schedule
- **Early Detection**: Catches failures before they impact lineage or profiling jobs
- **Owner Accountability**: Routes alerts to the correct stewards based on Collibra metadata

## Business Value

### Operational Integrity
**Challenge**: Connection failures often go unnoticed until critical profiling or lineage jobs fail in production.

**Solution**: Proactive connectivity testing ensures Collibra metadata reflects the true operational state of your data ecosystem.

### Accountability Reinforcement
**Challenge**: Large organizations struggle to identify who should fix broken Edge connections.

**Solution**: Automated mapping from failed connections to database assets and their owners ensures alerts reach the right people.

### Audit & Compliance
**Challenge**: Compliance audits require proof that governance controls are actively monitored.

**Solution**: Structured logs and summary reports provide a verifiable audit trail of all connection tests and owner notifications.

## How it Works: The Governance Control Loop

This control implements an automated feedback loop between your physical data infrastructure and your Collibra governance policies.

```mermaid
graph TD
    subgraph Cloud["Governance & Accountability - Collibra Cloud"]
        Asset[Database Asset - Catalog]
        Owner[Accountable Owner - Steward/Admin]
    end

    subgraph Controls["Operational Integrity Layer - governance_controls"]
        Control[Validation Control - test_edge_connections]
        Logic[Impact & Ownership Mapping Logic]
    end

    subgraph Infra["Infrastructure - Hybrid Security"]
        Edge[Collibra Edge Site]
        Source[(Data Source - Snowflake/S3/etc)]
    end

    Control -->|1. Trigger Test| Edge
    Edge <-->|2. Connectivity Probe| Source
    Edge -.->|3. Report Failure| Control
    Control -->|4. Analyze Impact| Logic
    Logic -->|5. Cross-Reference| Asset
    Asset -->|6. Identify Accountable| Owner
    Control -->|7. Send Alert| Owner
    Owner -.->|8. Fix Connection| Source
```

### Step-by-Step Business Process

The orchestrator executes this workflow for each governed Edge Site:

1. **Discovery**: Queries the Edge GraphQL API to list all child connections under the specified Edge Site(s) or individual connection ID(s).

2. **Heuristic Filtering**: Each connection is evaluated by the `ConnectionTestHeuristic`:
   - JDBC connections are always testable (standard database drivers)
   - Blacklisted types are skipped: PowerBI, Azure Lineage, Technical Lineage
   - Generic connections are testable if they have data-source parameters (connection-string, driver-class, host, etc.)
   - Connections with only `authType` configuration (OAuth shells) are skipped

3. **Parallel Testing**: Testable connections are submitted to a `ThreadPoolExecutor`. For each connection:
   - A `connectionTestConnection` GraphQL mutation is sent to the Edge API
   - The mutation returns a `jobId` representing the async test job
   - The `JobPoller` monitors the job via `jobById` GraphQL queries

4. **Job Polling**: The poller watches each job until a terminal state:
   - **Success states**: `COMPLETED`, `SUCCESS`, `SUCCEEDED`, `DONE`
   - **Failure states**: `FAILED`, `ERROR`, `CANCELLED`
   - **Timeout**: Global timeout (default 60s) prevents indefinite waiting
   - **SUBMITTED timeout**: Jobs stuck in SUBMITTED for too long are treated as failures

5. **Impact Mapping**: For each failed connection, the `ImpactMapper`:
   - Queries the Catalog Database API to find all `DatabaseConnection` records linked to the failed Edge connection
   - For each `DatabaseConnection` with a `database_id`, retrieves the database asset
   - Extracts `ownerIds` from the database asset
   - Fetches user details (name, email) for each unique owner via REST v2.0

6. **Owner Notification**: Failed connections trigger notifications:
   - The configured `NotificationHandler` receives the connection, error message, and owner info
   - Console handler logs alerts; Email/Slack handlers can be plugged in

7. **Reporting**: The `GovernanceReporter` generates:
   - Per-connection test results (pass/fail with timing)
   - Aggregate summary (total tested, passed, failed, success rate)
   - Impacted database assets with owner contact details
   - Full audit trail in structured log format

**The Control Loop**: Technical failures are automatically detected, analyzed for business impact, mapped to the correct asset owners, and routed for remediation.

## Architecture

This control uses a modular design for maintainability and testability:

### Core Components

**`GovernanceOrchestrator`** (`logic/orchestrator.py`)
- Main workflow coordinator with three entry points:
  - `run()` - Batch testing of all connections under Edge Sites
  - `test_individual_connections()` - Direct testing of specific connection IDs
  - `test_connections_in_edge_site()` - Targeted testing within an Edge Site context
- Manages parallel execution with ThreadPoolExecutor
- Orchestrates discovery, filtering, testing, impact mapping, and reporting

**`JobPoller`** (`logic/poller.py`)
- Monitors async job status with configurable timeout handling
- Automatic fallback: tries REST API first, falls back to GraphQL for Edge jobs
- Handles SUBMITTED state with separate timeout (stale job detection)
- Error categorization: network, authentication, resource not found

**`ImpactMapper`** (`logic/impact_mapper.py`)
- Maps failed Edge connections to Catalog database assets via the Catalog Database API
- Retrieves owner IDs from database asset metadata
- Deduplicates owners across multiple assets
- Fetches user details (name, email, username) from REST v2.0

**`GovernanceReporter`** (`logic/reporter.py`)
- Generates structured logs with timestamps and visual hierarchy
- Creates human-friendly summary reports with pass/fail counts and success rate
- Formats impacted asset details and owner notification records

**`ConnectionTestHeuristic`** (`logic/heuristic.py`)
- Filters connections based on type (skip PowerBI, Azure Lineage, Technical Lineage)
- JDBC family connections are always testable
- Generic connections are evaluated by inspecting their parameters for data-source keys
- Prevents false positives from non-database sources

**`ConnectionMonitor`** (`connection_monitor.py`)
- Simplified alternative to the orchestrator for single-connection testing
- Provides `test_connection()` and `test_and_notify()` convenience methods
- Uses the Catalog Database API for connection discovery

## Usage

### Finding IDs

- **Edge Site ID**: Navigate to Collibra → Settings → Edge → Sites. The ID is in the URL: `.../settings/edge/sites/<EDGE_SITE_ID>`
- **Connection ID**: Navigate to Collibra → Settings → Edge → Sites → [Select Site] → Connections. The ID is in the URL or can be copied from the connection details page.

### Execution Methods

The main script supports four execution modes. **Priority order**: `(--edge-site-id + --connection-id)` > `--connection-id` > `--edge-site-id` > `--yaml-config`

#### Method 1: Specific Connections within Edge Site (Contextual Targeted Testing)

Test specific connections within an Edge Site context. Provides Edge Site metadata in logs and notifications while only testing the connections you specify:

```bash
# Test specific connections within an Edge Site
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --edge-site-id 7d343ace-eecf-4c8c-af2c-3420280e6a2d \
  --connection-id abc123 \
  --connection-id def456

# With custom settings
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --edge-site-id 7d343ace-eecf-4c8c-af2c-3420280e6a2d \
  --connection-id abc123 \
  --max-workers 5 \
  --job-timeout 120
```

**Use Case**: Test specific problematic connections while maintaining Edge Site context for better tracking and notifications.

**Note**: Only one `--edge-site-id` can be specified when using `--connection-id`. The script validates (with a warning) if connections belong to the specified Edge Site, but will still test them.

#### Method 2: Individual Connection IDs (Direct Testing)

Test specific connections directly without Edge Site context:

```bash
# Test a single connection
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --connection-id abc123-connection-uuid

# Test multiple connections
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --connection-id abc123 \
  --connection-id def456 \
  --connection-id ghi789
```

**Use Case**: Quick testing of specific problematic connections without discovering the entire Edge Site or requiring Edge Site context.

#### Method 3: Edge Site IDs (Batch Testing)

Test all connections under specific Edge Sites:

```bash
# Test a single Edge Site
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --edge-site-id 7d343ace-eecf-4c8c-af2c-3420280e6a2d

# Test multiple Edge Sites
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --edge-site-id 7d343ace-eecf-4c8c-af2c-3420280e6a2d \
  --edge-site-id another-edge-site-id
```

**Use Case**: Test all connections within a specific Edge Site or environment.

#### Method 4: YAML Configuration File (Governed Scope)

For managing multiple Edge Sites in version control, use `governed_connections.yaml`:

```yaml
governed_connections:
  "7d343ace-eecf-4c8c-af2c-3420280e6a2d":
    name: "Production Edge Site"
    description: "Main production Snowflake connections"
    environment: "production"
    owner_team: "Data Platform Team"

  "another-edge-site-id":
    name: "Development Edge Site"
    description: "Development and testing connections"
    environment: "development"
    owner_team: "Data Engineering Team"
```

Run with YAML config:
```bash
# Use default governed_connections.yaml
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py

# Use custom YAML file
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --yaml-config /path/to/config.yaml
```

**Use Case**: Automated/scheduled governance validation of a fixed set of Edge Sites.

### CLI Options Reference

| Option | Description | Default |
|--------|-------------|---------|
| `--connection-id ID` | Individual connection ID to test (repeatable) | None |
| `--edge-site-id ID` | Edge Site ID to test (repeatable; max 1 with `--connection-id`) | None |
| `--yaml-config PATH` | Path to YAML configuration file | `governed_connections.yaml` |
| `--max-workers N` | Maximum parallel workers for connection testing | 3 |
| `--poll-delay N` | Seconds between job status polls | 5 |
| `--job-timeout N` | Maximum seconds to wait for job completion | 60 |

### Expected Output

Example output from a batch test:
```
2026-03-01 10:15:30 [INFO] Loading configuration...
2026-03-01 10:15:31 [INFO] Connection successful
2026-03-01 10:15:31 [INFO] ================================================================================
2026-03-01 10:15:31 [INFO]   GOVERNANCE CONNECTION TESTING STARTED
2026-03-01 10:15:31 [INFO] ================================================================================
2026-03-01 10:15:32 [INFO] [1/1] Edge Site: Production Edge Site
2026-03-01 10:15:33 [INFO]     SKIPPED: Azure Lineage Connector (Type: tech-lineage - not testable)
2026-03-01 10:15:33 [INFO]     Testing: Snowflake Production DW
2026-03-01 10:15:38 [INFO]     PASSED: Snowflake Production DW
2026-03-01 10:15:38 [INFO]     Testing: Databricks Dev Cluster
2026-03-01 10:15:43 [INFO]     FAILED: Databricks Dev Cluster
2026-03-01 10:15:43 [INFO]       Reason: Authentication/credential issue - Invalid token
2026-03-01 10:15:43 [INFO] ================================================================================
2026-03-01 10:15:43 [INFO]   TEST RESULTS SUMMARY
2026-03-01 10:15:43 [INFO] ================================================================================
2026-03-01 10:15:43 [INFO]   Total Connections Tested: 2
2026-03-01 10:15:43 [INFO]   Passed: 1 connection(s)
2026-03-01 10:15:43 [INFO]   Failed: 1 connection(s)
2026-03-01 10:15:43 [INFO]   Success Rate: 50.0%
```

## Testing

### Prerequisites

Authentication must be configured in `.env` before running any tests.

### Verify Authentication

```bash
# Quick OAuth connection check
uv run python governance_controls/test_edge_connections/test_connection_simple.py
```

### Automated Test Suite

The control has integration tests in `tests/integration/governance_controls/test_edge_connections/`:

```bash
# Run all orchestrator tests
uv run pytest tests/integration/governance_controls/test_edge_connections/test_orchestrator.py -v

# Run a specific test
uv run pytest tests/integration/governance_controls/test_edge_connections/test_orchestrator.py::test_orchestrator_test_individual_connections -v
```

**Available Tests**:

| Test | What it validates |
|------|-------------------|
| `test_orchestrator_initialization` | Orchestrator components are wired correctly |
| `test_orchestrator_run_smoke` | Full Edge Site workflow completes without crashing |
| `test_orchestrator_test_individual_connections` | Direct connection ID testing works end-to-end |
| `test_orchestrator_test_connections_in_edge_site` | Contextual Edge Site + connection ID testing works |
| `test_orchestrator_test_individual_connections_invalid_id` | Invalid connection IDs are handled gracefully |

### Full Project Test Suite

```bash
# Run all tests (SDK + governance controls)
uv run pytest -v

# Run with coverage report
uv run pytest --cov=collibra_client --cov-report=term-missing
```

## Utility Scripts

The following scripts are available for debugging and exploration. They are standalone and can be run independently.

| Script | Purpose | Usage |
|--------|---------|-------|
| `test_connection_simple.py` | Verify OAuth authentication works | `uv run python governance_controls/test_edge_connections/test_connection_simple.py` |
| `test_database_connections_simple.py` | List governed database connections | `uv run python governance_controls/test_edge_connections/test_database_connections_simple.py` |
| `list_site_connections.py` | List all connections for an Edge Site (tabular) | `uv run python governance_controls/test_edge_connections/list_site_connections.py <EDGE_SITE_ID>` |
| `test_connection_detail.py` | Fetch detailed metadata for a specific connection | `uv run python governance_controls/test_edge_connections/test_connection_detail.py <CONNECTION_ID>` |
| `debug_job_status.py` | Diagnose a job via both REST and GraphQL APIs | `uv run python governance_controls/test_edge_connections/debug_job_status.py <JOB_ID>` |
| `run_all_tests.sh` | Run utility scripts sequentially with rate-limit delays | `bash governance_controls/test_edge_connections/run_all_tests.sh` |

All utility scripts accept their required IDs as CLI arguments. No hardcoded values.

## Notification System

When a connection test fails, the control follows this workflow:

1. **Identify Impact**: Query Catalog API to find all database assets linked to the failed Edge connection
2. **Retrieve Owners**: Extract owner IDs from each affected database asset
3. **Deduplicate**: Remove duplicate owners across multiple assets
4. **Fetch Details**: Get user information (name, email) for each unique owner via REST v2.0
5. **Send Alerts**: Notify owners via configured handler (console, email, Slack)

### Notification Handlers

**Console Handler** (default): Logs formatted alerts to stdout. Color-coded output for visual scanning. Useful for development and CI/CD pipelines.

**Collibra Handler**: Can create tasks or update assets in Collibra (placeholder implementation, extend for your setup).

**Email Handler**: Sends alerts via SMTP (placeholder implementation, configure with your SMTP server).

**Adding a Custom Handler**: Implement the `NotificationHandler` abstract class:

```python
from governance_controls.test_edge_connections.notifications.handlers import NotificationHandler

class SlackNotificationHandler(NotificationHandler):
    def notify(self, connection, error_message, owner_info=None):
        # Send to Slack webhook
        ...
        return True
```

## Configuration Options

### Orchestrator Settings

```python
orchestrator = GovernanceOrchestrator(
    client=client,
    db_manager=db_manager,
    notification_handler=ConsoleNotificationHandler(),
    max_workers=3,          # Parallel execution threads
    poll_delay=5,           # Seconds between job status checks
    job_timeout=60          # Max seconds to wait for job completion
)
```

### Connection Filtering

The `ConnectionTestHeuristic` automatically skips non-testable connection types:
- PowerBI connections (BI tools, not data sources)
- Azure Lineage connectors (metadata only)
- Technical Lineage connectors
- OAuth shell connections with no data-source parameters

JDBC family connections are always considered testable.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `COLLIBRA_BASE_URL` | Yes | Collibra instance URL |
| `COLLIBRA_CLIENT_ID` | Yes (OAuth) | OAuth 2.0 client ID |
| `COLLIBRA_CLIENT_SECRET` | Yes (OAuth) | OAuth 2.0 client secret |
| `COLLIBRA_USERNAME` | Yes (Basic) | Username for Basic Auth |
| `COLLIBRA_PASSWORD` | Yes (Basic) | Password for Basic Auth |
| `COLLIBRA_TIMEOUT` | No | Request timeout in seconds (default: 30) |
| `COLLIBRA_LOG_FILE` | No | Path to log file for persistent logging |
| `COLLIBRA_GOVERNED_CONNECTIONS_CONFIG` | No | Override path to YAML config |

## Troubleshooting

### Common Issues

**Authentication fails (401)**:
- Verify credentials in `.env` are correct
- Check that the OAuth application has the required scopes in Collibra
- Run `test_connection_simple.py` to isolate authentication issues

**Rate limiting (429)**:
- Reduce `--max-workers` to lower parallel request volume
- Increase `--poll-delay` to space out polling requests
- Collibra enforces per-client rate limits; wait between runs

**Jobs stuck in SUBMITTED**:
- The Edge Site agent may be offline or overloaded
- Check Edge Site status in Collibra Settings → Edge → Sites
- The poller has a separate SUBMITTED timeout (default: 60s) to detect stale jobs

**All connections skipped**:
- The heuristic may be filtering out all connections
- Use `list_site_connections.py <EDGE_SITE_ID>` to inspect connection types
- Review the heuristic blacklist in `logic/heuristic.py`

**No impacted assets found**:
- Connections must be linked to Database assets in the Collibra Catalog
- Run `test_database_connections_simple.py` to check if connections have `database_id` values
- Ensure a Catalog refresh has been run for the Edge Site

## Key Features

- **Four Execution Modes**: Contextual, direct, batch, and governed-scope testing
- **Parallel Execution**: ThreadPoolExecutor with configurable workers (default: 3)
- **Robust Polling**: Automatic retry and GraphQL fallback for Edge jobs
- **Smart Filtering**: Heuristic-based connection type detection
- **Timeout Handling**: Global and per-state timeouts prevent indefinite waiting
- **Impact Mapping**: Automatic failure-to-owner resolution via Catalog and REST APIs
- **Colored Output**: Visual status indicators in console mode (TTY-aware)
- **Audit Trail**: Structured logs with timestamps and job IDs
- **Pluggable Notifications**: Abstract handler pattern for Console, Email, Slack, etc.
