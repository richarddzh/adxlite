---
description: "Use when implementing a new KQL scalar or aggregation function. Covers function implementation, UDF registration, null handling, and edge cases."
applyTo: "**/functions.py,**/aggregates.py"
---

# Skill: Adding a New KQL Function

## When to Use

When implementing a new KQL scalar or aggregation function.

## Steps

### 1. Classify the function

- **Aggregation**: Used inside `summarize` (e.g., `count()`, `sum()`, `dcount()`)
- **Scalar**: Used in any expression context (e.g., `tolower()`, `extract()`, `now()`)

### 2. Implement in adxpandas

**For scalar functions**, add to `adxpandas/src/adxpandas/functions.py`:

```python
def kql_my_func(arg1: Any, arg2: Any) -> Any:
    """Implements KQL my_func() semantics."""
    text = _safe_text(arg1)
    if text is None:
        return None
    return result
```

Then register in `adxpandas/src/adxpandas/engine/pandas_ops.py` under `_evaluate_function()`.

**For aggregations**, add handling in the `_evaluate_aggregation()` method.

### 3. Implement in adxlite

**For SQL-translatable functions**, add to `adxlite/src/adxlite/translator/functions.py`:

```python
"my_func": lambda args: f"kql_my_func({args[0]}, {args[1]})",
```

**If a SQLite UDF is needed**, add to `adxlite/src/adxlite/storage/udf.py` and register in `Database._register_udfs()`.

**For pandas fallback**, add in `adxlite/src/adxlite/engine/pandas_ops.py`.

### 4. Handle edge cases

- **Empty delimiter in split**: Return `list(text)` (each character)
- **Null inputs**: Always return None (use `_safe_text()` helper)
- **Type coercion**: `tostring()` on NaN produces `"nan"` in pandas 2.x — tests must account for this

### 5. Write tests

- Basic usage with various inputs
- Edge cases (empty string, zero, negative, None)
- Combination with other operators in pipeline
- Ensure tests work on pandas 2.x AND 3.x

## Rules

- Function names are case-insensitive (compare with `.lower()`)
- Always handle NULL inputs gracefully (return None)
- Use `?` parameter placeholders for literal values in SQL
- Validate argument count; raise `KqlParseError` for wrong arity
- `iif`/`iff` must wrap scalar args in `pd.Series` before using `.where()`
