# Contributing to Collibra Governance Automation Platform

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect differing viewpoints and experiences

## Getting Started

### Prerequisites

- Python 3.9 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip
- Git for version control
- A Collibra instance for testing (development or sandbox environment)

### Setup Development Environment

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/your-username/collibra-governance-automation.git
   cd collibra-governance-automation
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Collibra development instance credentials
   ```

4. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

5. **Verify installation**:
   ```bash
   uv run python governance_controls/test_edge_connections/test_connection_simple.py
   ```

## Development Workflow

### Branching Strategy

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `docs/*` - Documentation updates

### Creating a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### Making Changes

1. Make your changes in your feature branch
2. Write or update tests as needed
3. Update documentation if you're changing functionality
4. Ensure all tests pass
5. Commit your changes with clear, descriptive messages

## Coding Standards

### Python Code Style

This project follows these style guidelines:

- **Formatting**: Black (line length: 100)
- **Linting**: Ruff (pyflakes, pycodestyle, isort)
- **Type Checking**: MyPy (recommended but not strictly enforced)
- **Docstrings**: Google-style for public APIs

### Pre-commit Hooks

The project uses pre-commit hooks to enforce code quality:

```bash
# Run all hooks manually
pre-commit run --all-files

# Hooks will run automatically on git commit
```

### Code Quality Checks

Before submitting a pull request, ensure:

```bash
# Format code
black . --line-length=100

# Lint code
ruff check --fix

# Type checking
mypy collibra_client --ignore-missing-imports

# Run tests
uv run pytest
```

### Commit Message Guidelines

Write clear, descriptive commit messages:

```
<type>: <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example**:
```
feat: add support for Azure connections in heuristic filter

- Add Azure connection type detection
- Update connection test logic to handle Azure-specific parameters
- Add tests for Azure connection filtering

Closes #123
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/integration/catalog/test_database_connections.py

# Run with coverage
uv run pytest --cov=collibra_client --cov-report=term-missing

# Run integration tests only
uv run pytest -m integration
```

### Writing Tests

- Place tests in the `tests/` directory, mirroring the source structure
- Use descriptive test names: `test_<function>_<scenario>_<expected_result>`
- Use pytest fixtures for common setup (see `tests/conftest.py`)
- Integration tests require valid Collibra credentials in `.env`

**Example test**:
```python
def test_list_database_connections_returns_valid_connections(db_manager):
    """Test that list_database_connections returns valid connection objects."""
    connections = db_manager.list_database_connections(limit=10)

    assert isinstance(connections, list)
    assert len(connections) > 0

    for conn in connections:
        assert isinstance(conn, DatabaseConnection)
        assert conn.id is not None
        assert conn.name is not None
```

## Submitting Changes

### Pull Request Process

1. **Update your branch** with the latest changes from `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout your-feature-branch
   git rebase main
   ```

2. **Push your changes**:
   ```bash
   git push origin your-feature-branch
   ```

3. **Create a Pull Request** on GitHub with:
   - Clear title describing the change
   - Description of what changed and why
   - Reference to related issues (e.g., "Closes #123")
   - Screenshots or examples if applicable

4. **Address review feedback**:
   - Respond to comments
   - Make requested changes
   - Push updates to your branch

5. **Merge requirements**:
   - All tests must pass
   - Code must be reviewed and approved
   - No merge conflicts
   - Pre-commit hooks must pass

### Pull Request Template

```markdown
## Description
Brief description of the changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe the tests you ran and how to reproduce.

## Checklist
- [ ] Code follows the style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass
```

## Reporting Issues

### Bug Reports

When reporting bugs, include:

- **Description**: Clear description of the bug
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**:
  - Python version
  - Operating system
  - Collibra version
  - Package versions (`uv pip list`)
- **Logs**: Relevant error messages or logs
- **Screenshots**: If applicable

### Feature Requests

When requesting features, include:

- **Use Case**: Describe the problem you're trying to solve
- **Proposed Solution**: Your idea for how to solve it
- **Alternatives**: Other solutions you've considered
- **Additional Context**: Any other relevant information

## Project Structure

```
.
├── collibra_client/              # Reusable SDK
│   ├── core/                     # Authentication, HTTP client, config, exceptions
│   └── catalog/                  # Catalog Database API operations
├── governance_controls/          # Governance automation framework
│   └── test_edge_connections/    # Connection testing control
│       ├── logic/                # Business logic (orchestrator, poller, heuristic, etc.)
│       ├── notifications/        # Notification handlers (console, email, Collibra)
│       └── *.py                  # Utility/debug scripts (CLI-driven)
├── tests/                        # Test suite
│   └── integration/              # Integration tests (mirrors source structure)
├── pyproject.toml                # Dependencies and tooling config
├── CLAUDE.md                     # AI assistant guidance
└── CHANGELOG.md                  # Version history
```

## Additional Resources

- [Python Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [Black Code Style](https://black.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Collibra API Documentation](https://developer.collibra.com/)

## Questions or Need Help?

- Open an issue for questions about contributing
- Check existing issues and pull requests
- Review the project documentation

Thank you for contributing! 🎉
