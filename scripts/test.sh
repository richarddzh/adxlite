#!/usr/bin/env bash
# Run the test suite for adxlite.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

if [ ! -d ".venv" ]; then
    echo "Error: .venv not found. Run scripts/setup.sh first."
    exit 1
fi

echo "Running tests..."
.venv/bin/python -m pytest tests/ -v "$@"
