# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Multi-mode CLI for Edge Connection Testing**: Four execution modes for flexible testing
  - Contextual testing: Test specific connections within an Edge Site context (`--edge-site-id` + `--connection-id`)
  - Direct testing: Test specific connections by ID only (`--connection-id`)
  - Batch testing: Test all connections under Edge Sites (`--edge-site-id`)
  - Governed scope: Use YAML configuration file (default behavior)
- New orchestrator methods: `test_individual_connections()` and `test_connections_in_edge_site()`
- Comprehensive integration tests for new CLI modes
- Enhanced CLI help text with usage examples and priority documentation
- Updated documentation across all README files for consistency

### Changed
- Consolidated 3 debug job scripts (`debug_graphql_job.py`, `debug_graphql_job_final.py`, `diag_active_job.py`) into single `debug_job_status.py` with CLI argument
- Converted `test_connection_detail.py` from hardcoded ID to CLI argument
- All utility scripts now accept required IDs as CLI arguments (no hardcoded values)
- Removed deprecated `_get_basic_auth_header()` dead code from `DatabaseConnectionManager`

### Fixed
- Config validation order: partial credential errors (e.g. "client secret is missing") now fire before the generic "no credentials" error, restoring specific error messages
- Missing `logic/__init__.py` in `governance_controls/test_edge_connections/logic/` package
- Wrong `project_root` path in `test_database_connections_simple.py` (was one level too shallow)
- Removed `pre-commit` from main `dependencies` in `pyproject.toml` (dev-only dependency)
- Duplicate imports in `refresh_governed_connections.py` (consolidated into single import block)
- Incorrect environment variable names in documentation (`COLLIBRA_BASIC_AUTH_*` corrected to `COLLIBRA_USERNAME`/`COLLIBRA_PASSWORD`)
- f-string logger calls replaced with `%s` formatting across utility scripts (lazy evaluation best practice)
- Redundant `if attempt % 1 == 0` condition in `poller.py` (always true)
- Unreachable dead code in `owner.py` and `conftest.py`
- Wrong `PROJECT_DIR` in `run_all_tests.sh` (was one level too shallow), and `python3` replaced with `uv run python`

## [1.0.0] - 2026-03-01

### Initial Release
- Initial release of Collibra Governance Automation Platform
- Production-ready SDK (`collibra_client`) for Collibra API interactions
- Governance Controls framework for automated validation
- Edge Connection Validation control for testing data source connectivity
- Comprehensive documentation with READMEs, CLAUDE.md, and usage examples
- Integration test suite for SDK and controls
- Pre-commit hooks for code quality (black, ruff, mypy, isort)

### SDK Features
- OAuth 2.0 authentication with automatic token management
- Thread-safe token caching in `~/.collibra/token_cache/`
- Automatic token refresh on 401 responses
- Retry logic for transient failures (429, 5xx)
- REST v2.0 API support (Users, Jobs, Assets)
- Catalog Database API integration
- GraphQL support for Edge operations
- Comprehensive exception hierarchy

### Governance Controls Features
- Modular control architecture
- Edge Connection Validation control
  - Parallel connection testing with ThreadPoolExecutor
  - Job status polling with timeout handling
  - Connection type filtering (skip non-testable types)
  - Owner mapping and notification system
  - Enhanced log formatting with visual hierarchy
  - Accurate error categorization (network, auth, resource)
- Console, Email, and Collibra notification handlers

### Documentation
- Main README with architecture diagrams and quick start
- SDK README with comprehensive usage examples
- Governance Controls README with business value explanation
- Edge Connection Validation control README with detailed architecture
- CLAUDE.md for AI assistant guidance
- CONTRIBUTING.md with development guidelines
- LICENSE (MIT)
- Mermaid diagrams for visual architecture representation

---

## Version History

### Version Numbering

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality (backwards-compatible)
- **PATCH** version for backwards-compatible bug fixes

### Categories

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes

[Unreleased]: https://github.com/arnauudG/Collibra-Repository---Automations/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/arnauudG/Collibra-Repository---Automations/releases/tag/v1.0.0
