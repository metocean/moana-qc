# Moana-QC Contributing Guide

Thank you for your interest in contributing to the Moana Quality Control library!

## Development Setup

### Prerequisites

- Python 3.10 or later
- [uv](https://github.com/astral-sh/uv) package manager

### Installation with uv

```bash
# Clone the repository
git clone https://github.com/metocean/moana-qc.git
cd moana-qc

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install package with dev dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=moana_qc --cov-report=html

# Run specific test file
pytest moana_qc/tests/test_qc_tests.py
```

### Code Quality

This project uses modern Python tooling:

- **ruff**: Linting and formatting
- **mypy**: Type checking
- **pytest**: Testing
- **pre-commit**: Git hooks for code quality

```bash
# Format code
ruff format .

# Lint and auto-fix
ruff check --fix .

# Type checking
mypy moana_qc

# Run all checks (will run automatically on commit)
pre-commit run --all-files
```

### Making Changes

1. Create a new branch for your feature/fix
2. Make your changes
3. Ensure tests pass and code is formatted
4. Commit (pre-commit hooks will run automatically)
5. Push and create a pull request

## Code Style

- Follow PEP 8 (enforced by ruff)
- Use type hints where practical
- Write docstrings for public functions and classes
- Keep line length to 100 characters

## Testing

- Write tests for new functionality
- Maintain or increase code coverage
- Use descriptive test names

## Questions?

Contact: ops@metocean.co.nz or info@moanaproject.org
