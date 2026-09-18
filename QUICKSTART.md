# Quick Start: Cylc Branch

This is a quick reference for getting started with the modernized `cylc` branch.

## 🎯 What Changed?

- **Package names**: `ops_qc` → `moana_qc`, `ops_mangopare` → `moana_emails`
- **Python version**: 3.10+ (was 3.8)
- **Installation**: `uv` and virtual environments (no Docker)
- **Dependencies**: Modern versions, removed internal scheduler libs
- **Tooling**: `ruff`, `mypy`, `pytest`, `pre-commit`

## 🚀 Quick Setup

### Option 1: Automated (Recommended)

```bash
cd /source/moana-qc
bash setup_dev.sh
```

### Option 2: Manual

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup moana-qc
cd /source/moana-qc
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install

# Setup moana-emails
cd /source/ops-moana-emails
uv venv
source .venv/bin/activate
uv pip install -e ../moana-qc  # Install dependency
uv pip install -e ".[dev]"
pre-commit install
```

## 📦 Usage

### Import Changes

```python
# OLD (master branch)
from ops_qc import wrapper
from ops_qc.readers import ReadMangopare

# NEW (cylc branch)
from moana_qc import wrapper
from moana_qc.readers import ReadMangopare
```

### Running Tests

```bash
cd /source/moana-qc
source .venv/bin/activate
pytest                          # Run tests
pytest --cov=moana_qc          # With coverage
```

### Code Quality

```bash
ruff format .                   # Format code
ruff check --fix .              # Lint and auto-fix
mypy moana_qc                  # Type check
pre-commit run --all-files     # Run all checks
```

## 🔧 Development Workflow

1. **Make changes** to code
2. **Run formatter**: `ruff format .`
3. **Run linter**: `ruff check --fix .`
4. **Run tests**: `pytest`
5. **Commit** - pre-commit hooks run automatically

## 📚 Documentation

- [MODERNIZATION_SUMMARY.md](MODERNIZATION_SUMMARY.md) - Complete list of changes
- [MIGRATION.md](MIGRATION.md) - Migration guide from ops_qc
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines

## 🔗 Key Commands

```bash
# Development
uv pip install -e ".[dev]"     # Install with dev dependencies
pytest -v                       # Run tests verbosely
ruff check .                    # Check code quality
mypy moana_qc                  # Type checking

# Production/Cylc
pip install -e .                # Install package only
python -m moana_qc.wrapper      # Run wrapper

# Pre-commit
pre-commit install              # Install hooks
pre-commit run --all-files     # Run all hooks manually
```

## ⚡ For Cylc Workflows

```bash
# In Cylc workflow setup script
cd /source/moana-qc
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Update flow.cylc to use moana_qc instead of ops_qc
# Update config YAMLs as needed
```

## 🆘 Troubleshooting

### Import errors
```bash
# Ensure you're in the virtual environment
source .venv/bin/activate

# Reinstall in development mode
uv pip install -e .
```

### Test failures
```bash
# Update test imports from ops_qc to moana_qc
find . -name "test_*.py" -exec sed -i 's/ops_qc/moana_qc/g' {} +
```

### Dependency issues
```bash
# Clear cache and reinstall
rm -rf .venv
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## 📝 Next Steps After Setup

1. **Update imports** in your scripts: `ops_qc` → `moana_qc`
2. **Update Cylc configs** to reference new package names
3. **Run tests** to ensure everything works
4. **Review** [MODERNIZATION_SUMMARY.md](MODERNIZATION_SUMMARY.md) for complete details

## 🌟 Benefits of This Approach

- ✅ **Faster**: uv is 10-100x faster than pip
- ✅ **Reproducible**: Lock files ensure consistent installs
- ✅ **Modern**: Latest Python features and dependencies
- ✅ **Quality**: Automated code formatting and linting
- ✅ **Public**: No proprietary dependencies
- ✅ **Maintainable**: Industry-standard tooling

---

**Questions?** See [CONTRIBUTING.md](CONTRIBUTING.md) or contact ops@metocean.co.nz
