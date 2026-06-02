<#
.SYNOPSIS
    Run the test suites for adxpandas and adxlite.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "Error: .venv not found. Run scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "Running adxpandas tests..." -ForegroundColor Cyan
Push-Location (Join-Path $ProjectRoot "adxpandas")
try {
    & $Python -m pytest tests/ -v $args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }

Write-Host ""
Write-Host "Running adxlite tests..." -ForegroundColor Cyan
Push-Location (Join-Path $ProjectRoot "adxlite")
try {
    & $Python -m pytest tests/ -v $args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }

Write-Host ""
Write-Host "All tests passed!" -ForegroundColor Green
