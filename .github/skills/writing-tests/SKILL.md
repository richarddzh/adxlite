# Skill: Writing Tests for AdxLite

## When to Use

When adding new features, fixing bugs, or validating behavior.

## Test Structure

```python
import pandas as pd
import pytest
from adxlite import AdxLiteClient

@pytest.fixture
def client():
    """Create an in-memory client with sample data."""
    c = AdxLiteClient(":memory:")
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "age": [30, 25, 35],
        "city": ["NYC", "LA", "NYC"],
    })
    c.ingest_from_pandas("users", df)
    return c

def test_where_filter(client):
    result = client.query("users | where age > 28")
    assert len(result) == 2
    assert set(result["name"]) == {"Alice", "Charlie"}
```

## Conventions

- One test file per module or feature area.
- Test file naming: `tests/test_<feature>.py`.
- Use `pytest.fixture` for shared setup.
- Always use `:memory:` databases — never create files in tests.
- Test both happy paths and error cases.
- For parse errors: `pytest.raises(KqlParseError)`.
- For unsupported features: `pytest.raises(KqlUnsupportedError)`.
- Keep tests independent — no ordering dependency between tests.

## What to Test for Each New Feature

1. **Basic functionality** — does it work for the simplest case?
2. **Combination with other operators** — does it work in a pipeline with `where`, `project`, etc.?
3. **Edge cases** — empty tables, NULL values, empty strings, large numbers.
4. **Error cases** — invalid syntax, wrong argument count, type mismatches.
5. **Pipeline ordering** — ensure `| take 5 | where x > 1` applies take before where.

## Running Tests

```powershell
# From project root
scripts\test.ps1

# Or directly
.\.venv\Scripts\python.exe -m pytest tests/ -v
```
