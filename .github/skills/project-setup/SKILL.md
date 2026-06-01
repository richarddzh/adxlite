# Skill: Project Setup and Build

## When to Use

When setting up the project for the first time, or when the build/install is broken.

## Prerequisites

- Python 3.9+ installed and available as `python` (Windows) or `python3` (Linux/macOS).

## Setup Flow

```powershell
# Windows
scripts\setup.ps1

# Linux/macOS
./scripts/setup.sh
```

This will:
1. Create `.venv` if missing
2. Upgrade pip
3. Install adxlite in editable mode with dev dependencies

## Verifying the Install

```powershell
.\.venv\Scripts\python.exe -c "from adxlite import AdxLiteClient; print('OK')"
```

## Common Issues

| Issue | Fix |
|-------|-----|
| `OSError: Readme file does not exist: README.md` | Hatchling requires README.md to exist. Create it before installing. |
| `ModuleNotFoundError: No module named 'adxlite'` | Run `pip install -e .` inside the venv. The package must be installed in editable mode. |
| `hatchling.build has no attribute prepare_metadata_for_build_editable` | Upgrade pip: `.venv\Scripts\python.exe -m pip install --upgrade pip` |
| Tests import wrong version | Ensure you're running pytest from `.venv`, not system Python. Use `scripts\test.ps1`. |

## Key Rules

- **Never install into system/user Python**. Always activate or reference `.venv` explicitly.
- **`pyproject.toml` is the single source of truth** for all dependencies and build configuration.
- **Editable installs** (`pip install -e .`) allow code changes to take effect immediately without reinstalling.
