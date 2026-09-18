# Migration Guide: ops_qc → moana_qc

This guide helps you migrate from the legacy `ops_qc` package to the modern `moana_qc` package.

## Package Rename

The package has been renamed from `ops_qc` to `moana_qc` to reflect its public, open-source nature.

### Import Changes

**Before:**
```python
from ops_qc import wrapper
from ops_qc import apply_qc
from ops_qc.readers import ReadMangopare
```

**After:**
```python
from moana_qc import wrapper
from moana_qc import apply_qc
from moana_qc.readers import ReadMangopare
```

### Update Your Code

Use find-and-replace in your codebase:
- Replace `import ops_qc` with `import moana_qc`
- Replace `from ops_qc` with `from moana_qc`

## Dependency Changes

### Python Version

- **Minimum**: Python 3.10 (was 3.8)
- **Recommended**: Python 3.11 or 3.12

### Updated Dependencies

Major version updates:
- `numpy`: 1.21 → 1.26+
- `pandas`: 1.5 → 2.2+
- `xarray`: 2022.12 → 2024.1+
- `dask`: 2020.12 → 2024.1+
- `PyYAML`: <5 → 6.0+
- `shapely`: 1.8 → 2.0+

### Removed Dependencies

- `ops-core` (internal scheduler library)
- `ops-transfer` (internal scheduler library)

## Installation Changes

### Before (Docker-based)

```bash
docker build -f Dockerfile_MOS --build-arg GIT_TOKEN=${GIT_TOKEN} -t metocean/moana-qc:latest .
docker run -ti -v /source:/source -v /data:/data metocean/moana-qc:latest
```

### After (venv-based with uv)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv
source .venv/bin/activate

# Install package
uv pip install -e .
```

### For Cylc Workflows

```bash
cd /source/moana-qc
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration Files

All project configuration is now in `pyproject.toml`:

```toml
[project]
name = "moana-qc"
dependencies = [
    "numpy>=1.26.0",
    "pandas>=2.2.0",
    ...
]
```

The legacy `setup.py` has been removed. All configuration is defined in `pyproject.toml` following modern Python packaging standards (PEP 621).

## Development Workflow

### Before

```bash
# No standardized tools
pip install -r requirements/default.txt
pip install -r requirements/tests.txt
pytest
```

### After

```bash
# Modern tooling with pre-commit hooks
uv pip install -e ".[dev]"
pre-commit install

# Development commands
ruff format .           # Format code
ruff check --fix .      # Lint and auto-fix
mypy moana_qc          # Type checking
pytest                 # Run tests
```

## Cylc Workflow Integration

The package is now designed for Cylc workflows. See:
- [Cylc mangopare workflow README](/config/cylc-src-ops-test/mangopare/README.md)
- Workflow configuration files in `/config/cylc-src-ops-test/mangopare/etc/`

## Backward Compatibility Notes

### Temporary Import Alias (if needed)

If you need to maintain backward compatibility in existing code:

```python
# In your wrapper script
try:
    import moana_qc as ops_qc
except ImportError:
    import ops_qc  # Fallback to old package
```

### Version Detection

```python
from moana_qc import __version__

if __version__.startswith('1.'):
    # Modern moana_qc version
    print("Running modern moana-qc")
else:
    # Legacy ops_qc version
    print("Running legacy ops_qc")
```

## Breaking Changes

1. **Python 3.8/3.9 not supported** - Upgrade to Python 3.10+
2. **Package renamed** - Update all imports
3. **NumPy/Pandas APIs** - Some minor API changes in newer versions
4. **Docker removed** - Use virtual environments instead
5. **Internal libs removed** - `ops-core` and `ops-transfer` no longer required

## Questions?

- Technical issues: ops@metocean.co.nz
- Moana Project: info@moanaproject.org
- GitHub Issues: https://github.com/metocean/moana-qc/issues
