# Skill: Adding a New KQL Function

## When to Use

When implementing a new KQL scalar or aggregation function in adxlite.

## Steps

### 1. Classify the function

- **Aggregation**: Used inside `summarize` (e.g., `count()`, `sum()`, `dcount()`)
- **Scalar**: Used in any expression context (e.g., `tolower()`, `extract()`, `now()`)

### 2. Add to function registry

Edit `src/adxlite/translator/functions.py`:

```python
# In SCALAR_FUNCTIONS dict:
"my_func": lambda args: f"kql_my_func({args[0]}, {args[1]})",

# Or in AGG_FUNCTIONS dict for aggregations:
"my_agg": lambda args: f"kql_my_agg({args[0]})",
```

### 3. Implement the UDF (if needed)

If the function needs a SQLite UDF, add to `src/adxlite/storage/udf.py`:

```python
def kql_my_func(arg1: Any, arg2: Any) -> Any:
    """Implements KQL my_func() semantics."""
    if arg1 is None:
        return None
    return result
```

Then register it in `Database._register_udfs()` in `src/adxlite/storage/database.py`.

### 4. Add pandas fallback

In `src/adxlite/engine/pandas_ops.py`, add handling in:
- `_evaluate_function()` for direct pandas execution
- Or `_map_rowwise()` mapping dict for UDF-based row-wise execution

### 5. Write tests

- Basic usage with NULL handling
- Edge cases (empty string, zero, negative)
- Combination with other operators in pipeline

### 6. Update documentation

- `docs/reference/functions.md`: signature, description, example
- `.github/instructions.md`: supported functions list

## Rules

- Function names are case-insensitive (compare with `.lower()`)
- Always handle NULL inputs gracefully (return None)
- Use `?` parameter placeholders for literal values in SQL
- Validate argument count; raise `KqlParseError` for wrong arity
