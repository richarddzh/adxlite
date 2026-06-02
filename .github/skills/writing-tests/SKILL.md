---
name: writing-tests
description: Use this skill when writing or debugging tests for adxpandas or adxlite. Covers test structure, pandas version compatibility, and known pitfalls.
---

# Skill: Writing Tests for adxpandas / adxlite

## When to Use

When adding new features, fixing bugs, or validating behavior across the monorepo.

## Monorepo Structure

This project is a **monorepo** with two packages that share a parser:

- `adxpandas/` — Pure pandas KQL engine (has its own parser under `src/adxpandas/parser/`)
- `adxlite/` — SQLite-backed KQL engine (depends on adxpandas)

Tests for each package are run separately from their respective directories.

## Test Structure (adxpandas)

```python
from __future__ import annotations

import pandas as pd
import pytest

from adxpandas import AdxPandasClient


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "T": pd.DataFrame({
            "name": ["Alice", "Bob", "Charlie"],
            "age": [30, 25, 35],
            "city": ["NYC", "LA", "NYC"],
        })
    })


def test_where_filter() -> None:
    result = _client().query('T | where age > 28')
    assert len(result) == 2
    assert set(result["name"]) == {"Alice", "Charlie"}
```

## Test Structure (adxlite)

```python
import pandas as pd
import pytest
from adxlite import AdxLiteClient


@pytest.fixture
def client():
    c = AdxLiteClient(":memory:")
    df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
    c.ingest_from_pandas("users", df)
    return c


def test_where_filter(client):
    result = client.query("users | where age > 28")
    assert len(result) == 1
```

## Conventions

- **One test file per feature area** — e.g. `test_string_functions.py`, `test_aggregates.py`, `test_join_advanced.py`. Never use numeric suffixes like `test_exhaustive2.py`.
- Test file naming: `tests/integration/test_<feature>.py` or `tests/unit/test_<module>.py`.
- Use factory functions (e.g. `_client()`) for shared setup.
- Always use `:memory:` databases for adxlite — never create files in tests.
- Test both happy paths and error cases.
- For parse errors: `pytest.raises(KqlParseError)`.
- For unsupported features: `pytest.raises(KqlUnsupportedError)`.
- Keep tests independent — no ordering dependency between tests.

## Critical: Pandas Version Compatibility

**CI uses Python 3.10 + pandas 2.x. Local dev uses Python 3.12 + pandas 3.x.**

Tests MUST pass on both. Key differences:

| Behavior | pandas 2.x | pandas 3.x |
|----------|-----------|-----------|
| `None` in object column `.astype(str)` | becomes `"None"` (string) | stays as NaN |
| `strlen(None)` | returns `4` (len of "None") | returns NaN |
| `count()` dtype after left join | may be int64 or float64 | float64 (due to NaN) |
| `tostring(1)` vs `tostring(1.0)` | `"1"` | `"1.0"` |

**Rules to avoid CI failures:**

1. **Do NOT assert `pd.isna()` on string function results with null input** — behavior differs.
2. **Do NOT assert exact string representation of numeric counts** — accept both `"1"` and `"1.0"`.
3. **Avoid testing null-propagation behavior** — filter nulls out or use non-null test data.
4. **Use `in` for flexible assertions**: `assert result in ("1", "1.0")`.
5. **Always run tests locally AND check CI passes** before declaring work done.

## What to Test for Each New Feature

1. **Basic functionality** — does it work for the simplest case?
2. **Combination with other operators** — does it work in a pipeline?
3. **Edge cases** — empty tables, empty strings, large numbers.
4. **Error cases** — invalid syntax, wrong argument count, type mismatches.
5. **Pipeline ordering** — ensure `| take 5 | where x > 1` applies take before where.

## Running Tests

```powershell
# adxpandas tests (run from adxpandas directory)
Set-Location Q:\gitroot\adxlite\adxpandas
& Q:\gitroot\adxlite\.venv\Scripts\python.exe -m pytest tests/ --tb=short

# adxlite tests (run from adxlite directory)
Set-Location Q:\gitroot\adxlite\adxlite
& Q:\gitroot\adxlite\.venv\Scripts\python.exe -m pytest tests/ --tb=short
```

## Test Categories (integration)

| File | Covers |
|------|--------|
| `test_string_functions.py` | strlen, substring, indexof, strcat, split, replace_string, trim, tolower/toupper, countof, reverse |
| `test_string_predicates.py` | has, !has, contains, !contains, startswith, !startswith, endswith, !endswith |
| `test_regex_extract.py` | extract with regex patterns, group indices |
| `test_json_functions.py` | parse_json/todynamic, extractjson |
| `test_math_functions.py` | abs, sqrt, pow, log, floor, ceiling, round, toint, todouble |
| `test_datetime_functions.py` | now, ago, bin, datetime_diff, datetime_add, format_datetime |
| `test_in_between.py` | in, !in, between, !between |
| `test_aggregates.py` | count, sum, avg, min, max, dcount, countif, sumif, make_list/set, arg_max/min |
| `test_join_advanced.py` | All 9 join kinds, multiple on-columns |
| `test_let_bindings.py` | Scalar let, tabular let |
| `test_parse_operator.py` | parse with wildcards |
| `test_complex_pipelines.py` | Multi-stage pipelines (5-10 pipes) |
| `test_corner_cases.py` | Empty tables, single rows, iif scalar args |
| `test_negated_operators.py` | !in, !between, !has, !contains, !startswith, !endswith |
| `test_error_handling.py` | Invalid syntax, missing columns, unsupported operations |
| `test_stress.py` | 10000+ rows, many columns |
