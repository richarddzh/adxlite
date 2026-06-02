---
name: "Adding a KQL Operator"
description: "Step-by-step guide for implementing a new KQL tabular operator in the adxlite monorepo"
---

# Skill: Adding a New KQL Operator

## When to Use

When implementing a new KQL tabular operator (e.g., `| mv-expand`, `| union`).

## Architecture Note

The parser lives in `adxpandas/src/adxpandas/parser/` and is shared by both packages. Changes to parsing affect both adxpandas and adxlite.

## Steps

### 1. Define the AST node

In `adxpandas/src/adxpandas/parser/ast_nodes.py`:

```python
@dataclass(frozen=True)
class MyNewOp(Operator):
    """Represents | my_new_op ..."""
    some_field: str
    other_field: tuple[Expr, ...]
```

**Important**: `NamedExpr` is NOT a subclass of `Expr` — it's a wrapper with `expr: Expr` and `alias: str | None`. Use it for named expression lists (like `summarize by alias = expr`).

### 2. Update the tokenizer (if needed)

In `adxpandas/src/adxpandas/parser/tokenizer.py`:
- Add the operator keyword to the `KEYWORDS` set
- Hyphenated operators (like `project-away`) are handled automatically
- For negated operators (`!in`, `!has`), the tokenizer emits `KEYWORD "not"` + the keyword

### 3. Add parser logic

In `adxpandas/src/adxpandas/parser/parser.py`:
- Import the new AST node
- Add a case in `_parse_operator()`:

```python
if keyword == "my-new-op":
    return self._parse_my_new_op()
```

**Parser tips**:
- Use `_parse_named_expr_list()` for `alias = expr` patterns (e.g., summarize/extend)
- Use `_parse_expression_list()` for plain expressions (treats `=` as `==`)
- Check for keywords BEFORE calling expression parsers (e.g., `summarize by x` — check for `by` first)

### 4. Implement in adxpandas engine

In `adxpandas/src/adxpandas/engine/pandas_ops.py`:
- Add a handler in `PandasOperatorExecutor`

### 5. Implement in adxlite (choose execution strategy)

- **SQL-capable**: Translate in `adxlite/src/adxlite/translator/translator.py`
- **Pandas-only**: Execute in `adxlite/src/adxlite/engine/pandas_ops.py`

For SQL, add a case in `SqlTranslator._apply_operator()`:
```python
if isinstance(op, MyNewOp):
    return f"SELECT ... FROM ({source_sql}) AS _t ...", params
```

### 6. Update the planner

In `adxlite/src/adxlite/engine/planner.py`, classify the operator's SQL-capability and update schema inference.

### 7. Write tests for BOTH packages

- `adxpandas/tests/integration/` — test with AdxPandasClient
- `adxlite/tests/integration/` — test with AdxLiteClient
- Ensure tests pass on Python 3.10 + pandas 2.x (CI environment)

## Rules

- Each operator wraps previous pipeline as subquery: `SELECT ... FROM ({prev}) AS _t`
- Never string-interpolate user values — always parameterize
- Raise `KqlUnsupportedError` if truly unsupported
- Parser changes are shared — test both packages after modifying the parser
