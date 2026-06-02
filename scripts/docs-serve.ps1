#!/usr/bin/env pwsh
# Serve documentation locally with live-reload
# Access at http://127.0.0.1:8000/

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Push-Location $Root
try {
    & "$Root\.venv\Scripts\python.exe" -m mkdocs serve
} finally {
    Pop-Location
}
