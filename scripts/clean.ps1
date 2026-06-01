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
    if (Test-Path "*.egg-info" ) {
        Remove-Item -Recurse -Force *.egg-info
    }
    if (Test-Path "src\adxlite.egg-info") {
        Remove-Item -Recurse -Force "src\adxlite.egg-info"
    }
    Write-Host "Clean complete." -ForegroundColor Green
} finally {
    Pop-Location
}
