# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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

## [1.0.0] - 2026-03-01

### Initial Release
- First production-ready release of the platform
- Tested with Collibra Cloud instances
- Python 3.9+ compatibility
- Full integration test coverage

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
