<#
.SYNOPSIS
    Run the test suite for adxlite.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot
try {
    if (-not (Test-Path ".venv")) {
        Write-Host "Error: .venv not found. Run scripts\setup.ps1 first." -ForegroundColor Red
        exit 1
    }

    Write-Host "Running tests..." -ForegroundColor Cyan
    & .\.venv\Scripts\python.exe -m pytest tests/ -v $args
} finally {
    Pop-Location
}
