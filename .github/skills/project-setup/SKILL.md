---
name: project-setup
description: Use this skill when setting up the development environment, installing dependencies, or troubleshooting build issues in the adxlite monorepo.
---

# Skill: Project Setup and Build

## When to Use

When setting up the project for the first time, or when the build/install is broken.

## Prerequisites

- Python 3.10+ installed and available as `python` (Windows) or `python3` (Linux/macOS).

## Setup Flow

```powershell
# Windows
scripts\setup.ps1

# Or manually:
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e "./adxpandas[dev]"
& .\.venv\Scripts\python.exe -m pip install -e "./adxlite[dev]"
```

## Monorepo Layout

```
adxlite/               ← repo root
├── adxpandas/         ← Pure pandas KQL engine (owns the parser)
│   ├── src/adxpandas/
│   ├── tests/
│   └── pyproject.toml
├── adxlite/           ← SQLite-backed KQL engine (depends on adxpandas)
│   ├── src/adxlite/
│   ├── tests/
│   └── pyproject.toml
├── .venv/             ← Shared virtual environment
└── .github/
```

## Verifying the Install

```powershell
& .\.venv\Scripts\python.exe -c "from adxpandas import AdxPandasClient; print('adxpandas OK')"
& .\.venv\Scripts\python.exe -c "from adxlite import AdxLiteClient; print('adxlite OK')"
```

## Common Issues

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'adxpandas'` | Install: `pip install -e "./adxpandas[dev]"` |
| `ModuleNotFoundError: No module named 'adxlite'` | Install both; adxlite depends on adxpandas |
| Tests import wrong version | Ensure running pytest from `.venv`, not system Python |
| CI fails but local passes | pandas version difference — CI uses 2.x, local may use 3.x |
| `hatchling.build` error | Upgrade pip: `.venv\Scripts\python.exe -m pip install --upgrade pip` |

## Key Rules

- **Never install into system/user Python**. Always use `.venv`.
- **`pyproject.toml` is the single source of truth** for all dependencies and build configuration.
- **Editable installs** (`pip install -e .`) allow code changes to take effect immediately.
- **Install adxpandas before adxlite** — adxlite depends on the shared parser.
