# Copilot Agent Instructions

This file contains general instructions for Copilot agents working in this repository. It is NOT project documentation — it defines how you should plan, execute, and deliver work here.

---

## 1. Planning and Task Management

### Never lose track of requirements

When the user gives you multiple instructions across messages, you MUST:

1. Extract ALL requirements from the conversation — not just the latest message.
2. Maintain a plan (in your session state) with every requirement tracked.
3. Before starting work, list out all requirements and confirm nothing is missed.
4. Before declaring work complete, check every requirement against what was delivered.

### Work like a software engineer, not a code generator

Every non-trivial task should follow this lifecycle:

1. **Requirements analysis** — extract what is being asked, clarify ambiguity
2. **Design** — architecture decisions, tradeoffs, module boundaries
3. **Implementation** — write code with proper structure and quality
4. **Documentation** — user docs, API docs, design docs as appropriate
5. **Testing** — unit tests, integration tests, edge cases
6. **Verification** — run tests, run builds, confirm correctness
7. **Delivery** — commit, push, or report results

Do NOT skip steps. Do NOT jump straight to code for anything beyond trivial changes.

### Make tradeoffs explicit

For significant design decisions:

- Document alternatives considered
- State the chosen approach and why
- Note limitations and future improvements
- Put this in `docs/design/` for decisions that affect the architecture

---

## 2. Python Project Standards

### Environment management

- Use a local `.venv` virtual environment — NEVER install packages into the system or user-global Python.
- The `.venv` is created and managed via scripts in `scripts/`.
- Other developers should be able to run `scripts/setup-env.ps1` (Windows) or `scripts/setup-env.sh` (Unix) to prepare a development environment.

### Project structure

- Use `pyproject.toml` as the single source of truth for project metadata, dependencies, and build configuration.
- Use `hatchling` as the build backend.
- Source code lives under `src/<package_name>/` (src-layout).
- Tests live under `tests/` with `unit/` and `integration/` subdirectories.
- Documentation lives under `docs/` organized by audience (guides, reference, design).

### Dependency management

- Runtime dependencies in `pyproject.toml` under `[project.dependencies]`.
- Dev/test dependencies under `[project.optional-dependencies]` with a `dev` extra.
- Pin minimum versions but allow compatible upgrades (e.g., `pandas>=1.5.0`).

### Code quality

- All public functions and classes need Google-style docstrings.
- All public APIs need type hints.
- Avoid circular imports — follow the dependency direction defined in the architecture.
- Raise meaningful errors with context; never silently swallow failures.
- Use `quote_identifier()` for all dynamic SQL identifiers.
- Parameterize every literal in SQL with `?` placeholders.

---

## 3. Testing

### Running tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ -v
```

### Test standards

- Keep tests split between `tests/unit/` and `tests/integration/`.
- Use `:memory:` databases unless file persistence is specifically under test.
- Prefer deterministic assertions — use explicit `sort` before `take` in queries.
- Test edge cases: empty tables, NULL values, error paths, boundary conditions.
- Every new feature requires tests BEFORE the work is declared complete.

### Coverage expectations

- New operators/features: at minimum, happy path + error path + edge cases.
- Bug fixes: add a regression test that would have caught the bug.

---

## 4. Documentation

### Documentation types and locations

| Type | Location | Purpose |
| --- | --- | --- |
| User guides | `docs/guides/` | How-to for end users |
| API reference | `docs/reference/api.md` | Public Python API |
| Operator reference | `docs/reference/operators.md` | KQL operator syntax and examples |
| Function reference | `docs/reference/functions.md` | KQL function signatures |
| Syntax reference | `docs/reference/kql-syntax.md` | Formal grammar |
| Limitations | `docs/reference/limitations.md` | What is NOT supported |
| Architecture | `docs/design/architecture.md` | Internal module design |
| Design decisions | `docs/design/decisions.md` | Why things are the way they are |
| Requirements | `docs/design/requirements.md` | Feature requirements (FR-XX) |
| README | `README.md` | Project overview and quick start |

### Documentation rules

- When you add or change a feature, update ALL affected documentation files.
- Keep README.md in sync with actual capabilities — never list unsupported features as supported or vice versa.
- The `mkdocs.yml` navigation must include all doc pages.
- Run `mkdocs build --strict` to verify docs build without warnings.

---

## 5. DevOps and CI/CD

### Scripts

Scripts in `scripts/` provide reproducible developer workflows:

- `setup-env.ps1` / `setup-env.sh` — create .venv and install dependencies
- `run-tests.ps1` / `run-tests.sh` — activate venv and run pytest
- `build.ps1` / `build.sh` — build wheel and sdist
- `lint.ps1` / `lint.sh` — run linters if configured

### GitHub Workflows

- `.github/workflows/test.yml` — run tests on push/PR
- `.github/workflows/publish.yml` — publish to PyPI on release tag

### Commits

- Use conventional commit messages: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- Include a `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` trailer.
- Each commit should be a coherent, buildable unit. Don't commit broken states.

---

## 6. How to Respond to Instructions

### When the user gives a new requirement

1. Acknowledge the requirement.
2. Check it against existing work — does it conflict, extend, or complement?
3. Add it to your plan alongside all prior requirements.
4. Execute systematically: design → implement → test → document → verify.

### When the user says "don't forget previous requirements"

This means you have been losing context. Immediately:

1. Re-read your plan and any session checkpoints.
2. List all known requirements explicitly.
3. Show the user what you believe the full set of requirements is.
4. Proceed only after confirming nothing is missed.

### When the user says "don't rush to code"

This means you are skipping the design phase. Stop and:

1. Write design documentation first.
2. Evaluate tradeoffs and alternatives.
3. Get confirmation (or self-confirm in autopilot) before implementing.

### Completion checklist (before declaring any task done)

- [ ] All requirements from the conversation are addressed
- [ ] Code is implemented with proper module structure
- [ ] All tests pass (`pytest`)
- [ ] Documentation is updated (all affected files)
- [ ] Docs build clean (`mkdocs build --strict`)
- [ ] Changes are committed with meaningful message
- [ ] No TODO items remain unaddressed

---

## 7. Project-Specific Rules (adxlite)

These are implementation rules specific to this codebase:

- This is a LOCAL-ONLY engine. Never add remote cluster connectivity.
- Use nested subqueries to preserve KQL pipeline order in SQL.
- Store datetime columns as ISO-8601 text; restore from metadata on query.
- Register SQLite UDFs exactly once per connection.
- The hybrid execution model: SQL for what SQLite can handle, pandas for the rest.
- When adding new operators, decide SQL vs pandas routing in the planner.
- The parser is recursive-descent; extend it by adding new AST nodes and parse methods.
- Use `docs/design/requirements.md` to track feature requirements with FR-XX IDs.

## 7. Environment Rules

### Always use the project venv

All Python commands (pytest, pip install, python -c, etc.) MUST use the venv python:

```powershell
# Correct:
& Q:\gitroot\adxlite\.venv\Scripts\python.exe -m pytest tests/
& .\.venv\Scripts\python.exe -m pip install ipython

# Wrong — uses system Python, not the project venv:
python -m pytest tests/
pip install ipython
```

**Why:** The system Python may have different packages installed. Tests must run in the venv to reflect the actual project dependencies. Installing packages outside the venv pollutes the system and doesn't ensure reproducibility.

### Running tests

Tests must be run from each sub-project's directory so pytest picks up the correct `pyproject.toml`:

```powershell
Set-Location Q:\gitroot\adxlite\adxpandas
& Q:\gitroot\adxlite\.venv\Scripts\python.exe -m pytest tests/ --tb=short

Set-Location Q:\gitroot\adxlite\adxlite
& Q:\gitroot\adxlite\.venv\Scripts\python.exe -m pytest tests/ --tb=short
```

Or use the script: `.\scripts\test.ps1`
