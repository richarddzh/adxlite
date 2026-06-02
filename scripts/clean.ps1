<#
.SYNOPSIS
    Remove the virtual environment and build artifacts.
#>

$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot
try {
    if (Test-Path ".venv") {
        Write-Host "Removing .venv..." -ForegroundColor Cyan
        Remove-Item -Recurse -Force .venv
    }
    # Clean adxpandas build artifacts
    if (Test-Path "adxpandas\src\adxpandas.egg-info") {
        Remove-Item -Recurse -Force "adxpandas\src\adxpandas.egg-info"
    }
    if (Test-Path "adxpandas\dist") {
        Remove-Item -Recurse -Force "adxpandas\dist"
    }
    # Clean adxlite build artifacts
    if (Test-Path "adxlite\src\adxlite.egg-info") {
        Remove-Item -Recurse -Force "adxlite\src\adxlite.egg-info"
    }
    if (Test-Path "adxlite\dist") {
        Remove-Item -Recurse -Force "adxlite\dist"
    }
    Write-Host "Clean complete." -ForegroundColor Green
} finally {
    Pop-Location
}
