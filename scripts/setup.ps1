<# 
.SYNOPSIS
    Set up the development environment for adxlite.
.DESCRIPTION
    Creates a .venv virtual environment and installs the project
    in editable mode with dev dependencies.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot
try {
    # Create venv if it doesn't exist
    if (-not (Test-Path ".venv")) {
        Write-Host "[1/3] Creating virtual environment..." -ForegroundColor Cyan
        python -m venv .venv
    } else {
        Write-Host "[1/3] Virtual environment already exists." -ForegroundColor Green
    }

    # Activate and upgrade pip
    Write-Host "[2/3] Upgrading pip..." -ForegroundColor Cyan
    & .\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip

    # Install project in editable mode with dev dependencies
    Write-Host "[3/3] Installing adxlite in editable mode with dev dependencies..." -ForegroundColor Cyan
    & .\.venv\Scripts\python.exe -m pip install --quiet -e ".[dev]"

    Write-Host ""
    Write-Host "Done! Activate the environment with:" -ForegroundColor Green
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
} finally {
    Pop-Location
}
