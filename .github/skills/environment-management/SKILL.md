---
name: environment-management
description: >
  Use this skill when adding or removing dependencies, updating Python version requirements,
  or troubleshooting environment issues. Covers pyproject.toml management, venv rebuilding,
  and the minimal-dependency principle.
---

# Skill: Environment and Dependency Management

## When to Use

When adding/removing dependencies, updating Python version requirements, or troubleshooting environment issues.

## Rules

1. **Never install packages globally**. Always use the `.venv` in the project root.
2. **All dependencies declared in `pyproject.toml`** under `[project].dependencies` (runtime) or `[project.optional-dependencies].dev` (development).
3. **No `requirements.txt`** — `pyproject.toml` is the single source of truth.
4. **No `setup.py` or `setup.cfg`** — we use hatchling as the build backend.

## Adding a Runtime Dependency

1. Add to `pyproject.toml` under `dependencies`:
   ```toml
   dependencies = [
       "pandas>=1.5.0",
       "new-package>=x.y.z",
   ]
   ```
2. Reinstall: `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"`
3. Verify: `.\.venv\Scripts\python.exe -c "import new_package; print(new_package.__version__)"`

## Adding a Dev Dependency

1. Add to `pyproject.toml` under `[project.optional-dependencies].dev`:
   ```toml
   dev = [
       "pytest>=7.0",
       "new-dev-tool>=x.y.z",
   ]
   ```
2. Reinstall: `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"`

## Rebuilding the Environment

```powershell
scripts\clean.ps1
scripts\setup.ps1
```

## Principle: Minimal Dependencies

- Keep runtime dependencies as few as possible (currently just `pandas`).
- Do NOT add external Kusto/Azure SDK libraries — this project is self-contained.
- Prefer standard library solutions when possible.
