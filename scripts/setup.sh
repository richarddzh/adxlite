#!/usr/bin/env bash
# Set up the development environment for the monorepo.
# Creates a .venv virtual environment and installs both adxpandas
# and adxlite in editable mode with dev dependencies.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv .venv
else
    echo "[1/4] Virtual environment already exists."
fi

# Upgrade pip
echo "[2/4] Upgrading pip..."
.venv/bin/python -m pip install --quiet --upgrade pip

# Install adxpandas in editable mode with dev dependencies
echo "[3/4] Installing adxpandas in editable mode with dev dependencies..."
.venv/bin/python -m pip install --quiet -e "./adxpandas[dev]"

# Install adxlite in editable mode with dev dependencies
echo "[4/4] Installing adxlite in editable mode with dev dependencies..."
.venv/bin/python -m pip install --quiet -e "./adxlite[dev]"

echo ""
echo "Done! Activate the environment with:"
echo "  source .venv/bin/activate"
