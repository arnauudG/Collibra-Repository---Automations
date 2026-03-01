# Collibra Governance Automation Platform

A unified platform for building and running automated governance controls in Collibra. This repository is structured into two main pillars: a reusable SDK for Collibra API interactions and a modular framework for specific governance automations.

## Architecture Overview

### 1. Reusable SDK (`collibra_client`)

A production-ready, standalone Python library for any developer wanting to build custom integrations with Collibra.

**Key Features**:
- Standalone library that can be extracted and used in other projects
- OAuth 2.0 authentication with automatic token management
- Support for Catalog Database APIs and GraphQL
- Comprehensive error handling and retry logic

👉 [Read the SDK Documentation](./collibra_client/README.md)

### 2. Governance Controls (`governance_controls`)

A collection of automated, modular controls built on top of the SDK. This is the application layer that enforces policy and operational integrity.

**Key Features**:
- Modular, extensible framework for governance automation
- Pre-built controls for connection testing and validation
- Owner notification system for accountability
- Audit-ready reporting and logging

👉 [Explore Governance Controls](./governance_controls/README.md)

---

## The Governance Bridge

The platform operates as an operational integrity layer, bridging the gap between Collibra's cloud governance (Policies/Owners) and the on-premise/VPC data ecosystem (Reality).

```mermaid
graph LR
    subgraph "Business Context (Collibra Cloud)"
        P[Policies & Metadata]
        O[Accountable Owners]
    end

    subgraph "Operational Layer (Automation)"
        SDK[collibra_client SDK]
        CTRL[governance_controls]
    end

    subgraph "Technical Reality (Infrastructure)"
        E[Collibra Edge]
        D[(Data Sources)]
    end

    P -->|Defines Accountability| O
    CTRL -->|1. Validate Reality| E
    E <-->|2. Probe Connectivity| D
    CTRL -->|3. Map to Policy| P
    CTRL -->|4. Notify on Failure| O
```
*Figure 1: High-level overview of how the platform translates technical health into governance compliance.*

---

## Repository Structure

```
.
├── collibra_client/          # Reusable Python SDK
│   ├── core/                 # Auth, Auth Client, Config
│   ├── catalog/              # Catalog Database Manager
│   └── notifications/        # Reusable alert patterns
├── governance_controls/      # Automated Controls Framework
│   └── test_edge_connections/# Control: Edge Connectivity Validation
│       ├── logic/            # Modular business logic
│       └── README.md         # Detailed control documentation
├── tests/                    # Unified test suite (Core, Catalog, Controls)
├── governed_connections.yaml # Global configuration for governed scope
├── .env                      # Local environment credentials
└── pyproject.toml            # Project dependencies (uv/pip)
```

---

## Quick Start

### Prerequisites
- Python 3.9+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip.

### Installation

```bash
# Install dependencies using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your Collibra credentials:
# - COLLIBRA_BASE_URL
# - COLLIBRA_CLIENT_ID
# - COLLIBRA_CLIENT_SECRET
```

### Verify Installation

Test your OAuth connection:
```bash
uv run python governance_controls/test_edge_connections/test_connection_simple.py
```

### Run Your First Control

Execute the Edge Connection Validation control:
```bash
uv run python governance_controls/test_edge_connections/refresh_governed_connections.py
```

---

## Testing

The repository features a unified test suite using `pytest` with support for integration tests.

```bash
# Run all tests
uv run pytest

# Run integration tests only
uv run pytest -m integration

# Run with coverage
uv run pytest --cov=collibra_client --cov-report=term-missing

# Run specific test file
uv run pytest tests/integration/catalog/test_database_connections.py
```

See the [SDK Documentation](./collibra_client/README.md) for detailed testing instructions.

---

## Development

### Code Quality

```bash
# Install pre-commit hooks
pre-commit install

# Run all pre-commit hooks
pre-commit run --all-files

# Format code
black . --line-length=100

# Lint code
ruff check --fix

# Type checking
mypy collibra_client --ignore-missing-imports
```

### Project Structure

- **Line length**: 100 characters (enforced by black and ruff)
- **Python version**: 3.9+ (supports 3.9, 3.10, 3.11, 3.12)
- **Type hints**: Recommended but not strictly enforced
- **Docstrings**: Google-style for public APIs

---

## Future Roadmap

The platform is built for extensibility. Planned enhancements include:

- **Additional Controls**: Lineage verification, metadata completeness, data quality alerts
- **Enhanced SDK**: Expanded REST v2.0 endpoint coverage, improved GraphQL utilities
- **CI/CD Integration**: GitHub Actions workflows for automated governance validation
- **Notification Channels**: Email, Slack, and Teams integration for owner alerts

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
