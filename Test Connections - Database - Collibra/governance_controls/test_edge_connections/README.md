# Edge Connection Validation Control

This control validates the connectivity of data sources registered in Collibra Edge Sites. It automatically tests connections, monitors job status, and notifies owners when failures occur.

## Table of Contents

- [Overview](#overview)
- [Business Value](#business-value)
- [How it Works: The Governance Control Loop](#how-it-works-the-governance-control-loop)
- [Architecture](#architecture)
- [Usage](#usage)
- [Notification System](#notification-system)
- [Configuration Options](#configuration-options)
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

**The Control Loop**: Technical failures are automatically detected, analyzed for business impact, mapped to the correct asset owners, and routed for remediation.

## Architecture

This control uses a modular design for maintainability and testability:

### Core Components

**`GovernanceOrchestrator`** (`logic/orchestrator.py`)
- Main workflow coordinator
- Manages parallel execution with ThreadPoolExecutor
- Orchestrates refresh → poll → test → notify workflow

**`JobPoller`** (`logic/poller.py`)
- Monitors async job status with timeout handling
- Automatic fallback to GraphQL for Edge jobs
- Configurable polling interval and global timeout

**`ImpactMapper`** (`logic/impact_mapper.py`)
- Maps failed Edge connections to Catalog database assets
- Retrieves owner IDs from Catalog API
- Deduplicates owners across multiple assets

**`GovernanceReporter`** (`logic/reporter.py`)
- Generates structured logs with timestamps
- Creates human-friendly summary reports
- Formats owner notification payloads

**`ConnectionTestHeuristic`** (`logic/heuristic.py`)
- Filters connections based on type (skip PowerBI, Azure Lineage, etc.)
- Identifies testable vs. non-testable connection families
- Prevents false positives from non-database sources

## Usage

### Finding Edge Site IDs

Navigate to your Collibra instance → Settings → Edge → Sites. The Edge Site ID is in the URL: `.../settings/edge/sites/<EDGE_SITE_ID>`

### Execution Methods

#### Method 1: CLI Arguments (Recommended)

Test specific Edge Sites directly via command-line arguments:

```bash
# Test a single Edge Site
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --edge-site-id 7d343ace-eecf-4c8c-af2c-3420280e6a2d

# Test multiple Edge Sites
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --edge-site-id 7d343ace-eecf-4c8c-af2c-3420280e6a2d \
  --edge-site-id another-edge-site-id

# With custom settings
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --edge-site-id 7d343ace-eecf-4c8c-af2c-3420280e6a2d \
  --max-workers 5 \
  --poll-delay 3 \
  --job-timeout 120
```

**CLI Options**:
- `--edge-site-id ID`: Edge Site ID to test (can be specified multiple times)
- `--yaml-config PATH`: Path to YAML configuration file
- `--max-workers N`: Maximum parallel workers (default: 3)
- `--poll-delay N`: Seconds between job status polls (default: 5)
- `--job-timeout N`: Maximum seconds to wait for job completion (default: 60)

#### Method 2: YAML Configuration File

For managing multiple Edge Sites, create `governed_connections.yaml`:

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

### Testing Connection First

Verify your authentication is working:
```bash
uv run python governance_controls/test_edge_connections/test_connection_simple.py
```

### Expected Output

The control will:
1. Load governed Edge Site IDs from `governed_connections.yaml`
2. Refresh database connections for each Edge Site
3. Poll refresh jobs until completion (timeout: 60s per job)
4. Test each connection and poll test jobs
5. Map failed connections to database assets and owners
6. Send notifications (console by default)
7. Print a summary report

Example output:
```
2026-03-01 10:15:30 [INFO] Loading configuration...
2026-03-01 10:15:31 [INFO] Testing OAuth connection...
2026-03-01 10:15:32 [INFO] Connection successful
2026-03-01 10:15:32 [INFO] Refreshing connections for Edge Site: Production Edge Site
2026-03-01 10:15:35 [INFO] Refresh job completed: SUCCESS
2026-03-01 10:15:36 [INFO] Testing 12 connections...
2026-03-01 10:15:45 [INFO] All connection tests completed
2026-03-01 10:15:45 [INFO] Summary: 11 passed, 1 failed
```

## Notification System

When a connection test fails, the control follows this workflow:

1. **Identify Impact**: Query Catalog API to find all database assets linked to the failed connection
2. **Retrieve Owners**: Extract owner IDs from each affected database asset
3. **Deduplicate**: Remove duplicate owners across multiple assets
4. **Fetch Details**: Get user information (name, email) for each unique owner
5. **Send Alerts**: Notify owners via configured handler (console, email, Slack)

### Notification Payload

Each notification includes:
- **Connection Name**: Human-readable name from Edge API
- **Connection ID**: UUID for tracking
- **Database Assets**: List of affected database IDs
- **Owner Information**: Name and email of accountable steward
- **Failure Details**: Error message from connection test job

### Notification Handlers

**Console Handler** (default):
- Prints formatted alerts to stdout
- Color-coded output for quick visual scanning
- Useful for development and debugging

**Future Handlers**:
- Email: Send alerts via SMTP
- Slack: Post to designated channels
- Teams: Microsoft Teams webhook integration

## Configuration Options

### Orchestrator Settings

Configure in the main script:

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
- Other non-database connection families

## Key Features

- **Parallel Execution**: ThreadPoolExecutor with configurable workers (default: 3)
- **Robust Polling**: Automatic retry and GraphQL fallback for Edge jobs
- **Smart Filtering**: Heuristic-based connection type detection
- **Timeout Handling**: Global timeout prevents indefinite waiting
- **Colored Output**: Visual status indicators in console mode
- **Audit Trail**: Structured logs with timestamps and job IDs
