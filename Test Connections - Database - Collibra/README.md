# Collibra governance automation platform

Python tooling to validate Collibra connectivity (via Edge Sites) and turn failures into actionable, owner-routed evidence.

This project is organized as:

- `collibra_client/`: a small SDK for Collibra REST + GraphQL (auth, retries, job polling)
- `governance_controls/`: runnable controls built on the SDK (enforcement logic, reporting, notifications)

Start here if you want to run the connection validation control:
`governance_controls/test_edge_connections/refresh_governed_connections.py`.

## Repository structure

```
.
├── collibra_client/                              # SDK (auth, REST/GraphQL, retries)
├── governance_controls/                          # Controls (enforcement + reporting)
│   └── test_edge_connections/                    # Connection validation control
├── tests/                                        # Integration tests (require credentials)
├── .env.example                                  # Environment template
├── pyproject.toml                                # Dependencies and tooling
└── README.md                                     # This file
```

## Requirements

- Python 3.9+
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`
- A Collibra instance you can authenticate against (OAuth2 or Basic Auth)

## Install

```bash
uv sync

# or
pip install -e .
```

## Configure

```bash
cp .env.example .env
```

Fill in `.env`. Use either OAuth2 (recommended for automation) or Basic Auth.

```bash
COLLIBRA_BASE_URL=https://your-instance.collibra.com
COLLIBRA_CLIENT_ID=your_client_id
COLLIBRA_CLIENT_SECRET=your_client_secret
```

```bash
COLLIBRA_BASE_URL=https://your-instance.collibra.com
COLLIBRA_USERNAME=your_username
COLLIBRA_PASSWORD=your_password
```

## Quick check

```bash
uv run python governance_controls/test_edge_connections/test_connection_simple.py
```

## Run the connection validation control

This control can test:
- specific connections (`--connection-id`)
- all connections under one or more Edge Sites (`--edge-site-id`)
- a governed perimeter defined in YAML (default config included)

```bash
# Targeted: specific connections within an Edge Site context
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --edge-site-id 7d343ace-eecf-4c8c-af2c-3420280e6a2d \
  --connection-id abc123 --connection-id def456

# Direct: specific connections by ID
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --connection-id abc123-connection-uuid

# Batch: all connections under an Edge Site
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py \
  --edge-site-id 7d343ace-eecf-4c8c-af2c-3420280e6a2d

# Governed scope: YAML-driven perimeter (default config)
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py
```

ID hints (Collibra UI):
- Edge Site ID: Settings → Edge → Sites (ID in URL)
- Connection ID: Settings → Edge → Sites → (site) → Connections (ID in URL/details)

See `governance_controls/test_edge_connections/README.md` for the full CLI reference,
expected output, and investigation scripts.

## Testing

Tests are integration-style and require a real Collibra instance + credentials in `.env`.

```bash
uv run pytest -v

# with coverage
uv run pytest --cov=collibra_client --cov-report=term-missing
```

## Development

```bash
# Install pre-commit hooks
pre-commit install

# Run all pre-commit hooks
pre-commit run --all-files

# Format + lint
black . --line-length=100
ruff check --fix

# Type checking
mypy collibra_client --ignore-missing-imports
```

## Troubleshooting

## Changelog

See `CHANGELOG.md`.

## License

MIT. See `LICENSE`.
