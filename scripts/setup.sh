#!/usr/bin/env bash
# Set up the development environment for adxlite.
# Creates a .venv virtual environment and installs the project
# in editable mode with dev dependencies.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv .venv
else
    echo "[1/3] Virtual environment already exists."
fi

# Upgrade pip
echo "[2/3] Upgrading pip..."
.venv/bin/python -m pip install --quiet --upgrade pip

# Install project in editable mode with dev dependencies
echo "[3/3] Installing adxlite in editable mode with dev dependencies..."
.venv/bin/python -m pip install --quiet -e ".[dev]"

echo ""
echo "Done! Activate the environment with:"
echo "  source .venv/bin/activate"
