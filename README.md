---
tags: []

category: Documentation
type: data/readme
complexity: intermediate
time_required: 15-30 minutes
created: 2026-02-18
status: active
last_updated: 2026-03-02
---

# Collibra governance automations

This repository groups small, Collibra-focused automation projects.

## Projects

### Governance automation platform

Location: `Test Connections - Database - Collibra/`

- Validates Collibra Edge connection health.
- Produces audit-friendly logs (what was tested, what passed/failed, when).
- Maps failures to impacted Catalog database assets and their owners.

Start here:
- [Platform README](Test%20Connections%20-%20Database%20-%20Collibra/README.md)
- [Controls](Test%20Connections%20-%20Database%20-%20Collibra/governance_controls/README.md)
- [Connection validation control](Test%20Connections%20-%20Database%20-%20Collibra/governance_controls/test_edge_connections/README.md)

## Quick start

```bash
cd "Test Connections - Database - Collibra"
uv sync
cp .env.example .env
uv run python governance_controls/test_edge_connections/test_connection_simple.py
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py
```

## Repository structure

```
.
├── README.md
└── Test Connections - Database - Collibra/
    ├── README.md
    ├── collibra_client/
    ├── governance_controls/
    ├── tests/
    ├── pyproject.toml
    └── uv.lock
```

## Requirements

- Python 3.9+
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`
- A Collibra instance you can authenticate against (OAuth2 or Basic Auth)
