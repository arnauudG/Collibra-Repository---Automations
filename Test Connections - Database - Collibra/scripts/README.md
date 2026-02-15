# Utility Scripts

Scripts for connection governing and quick checks. These are **not** pytest tests.

## Scripts

### `refresh_governed_connections.py` (primary)

Connection testing for your governed set: refresh each edge, wait for completion, **notify owners of failed connections**, and print a **summary report**.

**Usage:**
```bash
python3 scripts/refresh_governed_connections.py
```

**What it does:**
- Loads governed edge connection IDs from `governed_connections.yaml` (or `COLLIBRA_GOVERNED_CONNECTIONS_CONFIG`)
- For each governed edge: calls the Catalog refresh API, waits for the job to complete (polls until COMPLETED or ERROR), records result
- For each **failed** edge: lists database connections under that edge, fetches owners (`ownerIds`) for each database, and **notifies** each owner (console by default; you can plug in other handlers)
- Prints a **summary report**: succeeded/failed counts, failed databases and their owners, and list of notifications sent

Governs connections only; no metadata sync. The end goal is to notify owners when a connection test fails and have a clear summary report.

### `test_database_connections_simple.py`

List database connections, optionally limited to the governed set.

**Usage:**
```bash
python3 scripts/test_database_connections_simple.py
```

**What it does:**
- Loads `governed_connections.yaml` if present
- If governed IDs exist: refreshes only those edge connections, then lists and filters to connections whose `edge_connection_id` is in the governed set (and that have a database asset ID)
- If YAML is missing or empty: skips refresh and lists all connections with a database asset ID

### `test_connection_simple.py`

Quick OAuth connection test.

**Usage:**
```bash
python3 scripts/test_connection_simple.py
```

**What it does:**
- Loads configuration from `.env`
- Creates authenticated Collibra client
- Tests OAuth connection
- Fetches current user information

## Requirements

- `.env` file with Collibra credentials
- Dependencies installed (`uv sync` or `pip install -e .`)

For governed scripts, create `governed_connections.yaml` at project root (or set `COLLIBRA_GOVERNED_CONNECTIONS_CONFIG`). See main `README.md` for YAML format.
