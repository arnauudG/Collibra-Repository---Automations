# Connection validation control (`test_edge_connections`)

Validate Collibra Edge connections and produce an auditable pass/fail report. For failures, the control can map impact back to Catalog database assets and their owners (so alerts can go to the right people instead of a generic inbox).

The entry point is `governance_controls/test_edge_connections/refresh_governed_connections.py`.

## What this control does

1. Selects a perimeter (Edge Site IDs, connection IDs, or a YAML-defined governed scope).
2. Lists connections via the Edge GraphQL API.
3. Filters out non-testable connections using `logic/heuristic.py` (to reduce false positives).
4. Triggers Edge connection tests (GraphQL mutation).
5. Polls async jobs until completion (`logic/poller.py`).
6. Builds a summary report (`logic/reporter.py`).
7. For failed connections, maps impacted Catalog database assets and owners (`logic/impact_mapper.py`).
8. Sends notifications via a pluggable handler in `notifications/`.

## Requirements

- Python 3.9+
- Collibra instance URL + credentials in `.env` (`.env.example` shows all supported variables)
- An Edge Site reachable by your Collibra instance (the control triggers tests through Edge APIs)

## Quick start

```bash
uv sync
cp .env.example .env
uv run python governance_controls/test_edge_connections/test_connection_simple.py
```

Run the control (YAML governed scope by default):

```bash
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py
```

## Usage

The script supports four modes. Priority order is:
`(--edge-site-id + --connection-id)` > `--connection-id` > `--edge-site-id` > YAML config.

### Mode 1: Edge Site context + specific connections

```bash
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --edge-site-id <EDGE_SITE_ID> \
  --connection-id <CONNECTION_ID_1> \
  --connection-id <CONNECTION_ID_2>
```

### Mode 2: Specific connection IDs (no Edge Site context)

```bash
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --connection-id <CONNECTION_ID_1> \
  --connection-id <CONNECTION_ID_2>
```

### Mode 3: Full Edge Site (all connections under one or more sites)

```bash
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --edge-site-id <EDGE_SITE_ID_1> \
  --edge-site-id <EDGE_SITE_ID_2>
```

### Mode 4: Governed scope (YAML)

```bash
# Use default config
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py

# Or provide a custom file
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --yaml-config /path/to/config.yaml
```

### CLI options

| Option | Notes | Default |
|---|---|---|
| `--connection-id ID` | Repeatable | none |
| `--edge-site-id ID` | Repeatable; only one allowed when using `--connection-id` | none |
| `--yaml-config PATH` | Overrides the governed scope file | none |
| `--max-workers N` | Parallelism for connection tests | `3` |
| `--poll-delay N` | Seconds between job status polls | `5` |
| `--job-timeout N` | Max seconds to wait for a job | `60` |

## Governed scope configuration (YAML)

By default, governed scope is loaded from:

- `COLLIBRA_GOVERNED_CONNECTIONS_CONFIG` if set, otherwise
- `governance_controls/test_edge_connections/governed_connections.yaml`

Example structure:

```yaml
governed_connections:
  "7d343ace-eecf-4c8c-af2c-3420280e6a2d":
    name: "Production Edge Site"
    description: "Main production connections"
    environment: "production"
    owner_team: "Data Platform"
```

The YAML keys are Edge Site IDs. The metadata fields are optional; they are used for clearer logs and notifications.

## Output and logging

- The script logs progress and prints a final summary with counts and success rate.
- To persist logs to a file, set `COLLIBRA_LOG_FILE=/path/to/logfile.log`.

## Investigation scripts

When a run fails (or everything is skipped), these scripts help narrow down the issue:

| Script | Purpose |
|---|---|
| `test_connection_simple.py` | Sanity-check authentication and basic API access |
| `list_site_connections.py <EDGE_SITE_ID>` | List connections under an Edge Site (types + names) |
| `test_connection_detail.py <CONNECTION_ID>` | Inspect one connection’s details/config |
| `test_database_connections_simple.py` | Inspect Catalog database connections and `database_id` mappings |
| `debug_job_status.py <JOB_ID>` | Compare job status sources (REST vs GraphQL) |
| `run_all_tests.sh` | Runs multiple investigations sequentially (with delays) |

## Notifications

Notification handlers live under `governance_controls/test_edge_connections/notifications/`.

- Default handler: `ConsoleNotificationHandler` (prints owner + impact details)
- To add a handler, implement the `NotificationHandler` interface in
  `notifications/handlers.py` and wire it in `refresh_governed_connections.py`.

## Troubleshooting

### Authentication fails (401)

- Re-check `.env` values (base URL and credentials).
- Ensure `COLLIBRA_BASE_URL` does not end with a trailing slash.
- If using OAuth2, verify the OAuth app in Collibra is enabled and allowed to call the needed APIs.

### Rate limiting (429)

- Lower `--max-workers`.
- Increase `--poll-delay`.
- Avoid running multiple instances of the control concurrently.

### Jobs stuck in `SUBMITTED`

- Edge agent may be offline/overloaded.
- Check Edge Site status in the Collibra UI.
- Increase `--job-timeout` to account for slow environments.

### No impacted assets found for failures

- Mapping relies on connections being linked to Catalog database assets.
- Use `test_database_connections_simple.py` to confirm `database_id` mappings exist.

### Everything is skipped

- The heuristic filters out non-database / non-testable connections.
- Use `list_site_connections.py <EDGE_SITE_ID>` and review `logic/heuristic.py`.
