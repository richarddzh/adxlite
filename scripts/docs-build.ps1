#!/usr/bin/env pwsh
# Build documentation as static HTML into site/ directory
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Push-Location $Root
try {
    & "$Root\.venv\Scripts\python.exe" -m mkdocs build --strict
    Write-Host "Documentation built to site/ directory" -ForegroundColor Green
} finally {
    Pop-Location
}
