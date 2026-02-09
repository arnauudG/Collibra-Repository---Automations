# Collibra Repository - Features & Automations

This repository contains various projects and automations for Collibra Data Intelligence Cloud.

## Projects

### Database Connection Synchronization & Monitoring

**Location:** `Test Connections - Database - Collibra/`

An automated tool for testing, synchronizing, and monitoring database metadata synchronization jobs in Collibra. This tool identifies failed database synchronizations, retrieves database owner information, and sends notifications to owners about synchronization failures.

**Key Features:**
- Automated metadata synchronization for all cataloged database connections
- Job status monitoring and failure detection
- Owner information retrieval from Catalog Database API
- Automatic notification sending to database owners for failures
- Comprehensive reporting with owner details

**Quick Start:**
```bash
cd "Test Connections - Database - Collibra"
python3 main.py
```

See the [project README](Test%20Connections%20-%20Database%20-%20Collibra/README.md) for detailed documentation.

## Repository Structure

```
.
├── README.md (this file)
└── Test Connections - Database - Collibra/
    ├── README.md (project-specific documentation)
    ├── main.py (main orchestrator script)
    ├── collibra_client/ (Python client library)
    ├── scripts/ (utility scripts)
    └── tests/ (test suite)
```

## Requirements

- Python 3.9+
- [`uv`](https://github.com/astral-sh/uv) package manager (recommended) or pip
- Collibra instance with OAuth application configured

## Getting Started

Each project has its own README with specific setup instructions. Navigate to the project directory and follow the instructions in its README.

## Contributing

Each project maintains its own code quality standards and testing requirements. Refer to individual project READMEs for contribution guidelines.

## License

MIT

