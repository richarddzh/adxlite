#!/usr/bin/env bash
# Run the test suites for adxpandas and adxlite.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

PYTHON="$PROJECT_ROOT/.venv/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "Error: .venv not found. Run scripts/setup.sh first."
    exit 1
fi

echo "Running adxpandas tests..."
cd "$PROJECT_ROOT/adxpandas"
"$PYTHON" -m pytest tests/ -v "$@"

echo ""
echo "Running adxlite tests..."
cd "$PROJECT_ROOT/adxlite"
"$PYTHON" -m pytest tests/ -v "$@"

echo ""
echo "All tests passed!"
