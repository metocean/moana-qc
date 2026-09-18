#!/bin/bash
# Setup script for moana-qc development environment using uv

set -e

echo "🚀 Setting up moana-qc development environment..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo "✅ uv is installed"

# Create virtual environment
echo "🔨 Creating virtual environment..."
uv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install package with dev dependencies
echo "📚 Installing moana-qc with development dependencies..."
uv pip install -e ".[dev]"

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install

echo ""
echo "✨ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "  1. Activate the environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  2. Run tests:"
echo "     pytest"
echo ""
echo "  3. Format and lint code:"
echo "     ruff format ."
echo "     ruff check --fix ."
echo ""
echo "  4. Type check:"
echo "     mypy moana_qc"
echo ""
echo "  5. Run all quality checks:"
echo "     pre-commit run --all-files"
echo ""
