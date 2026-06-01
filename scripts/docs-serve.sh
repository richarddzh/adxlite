#!/usr/bin/env bash
# Serve documentation locally with live-reload
# Access at http://127.0.0.1:8000/
set -e
cd "$(dirname "$0")/.."
.venv/bin/python -m mkdocs serve
