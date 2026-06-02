#!/usr/bin/env bash
# Remove the virtual environment and build artifacts.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

if [ -d ".venv" ]; then
    echo "Removing .venv..."
    rm -rf .venv
fi

rm -rf adxpandas/src/adxpandas.egg-info adxpandas/dist
rm -rf adxlite/src/adxlite.egg-info adxlite/dist

echo "Clean complete."
