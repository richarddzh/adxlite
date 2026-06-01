# Skill: Adding a New KQL Operator

## When to Use

When implementing a new KQL tabular operator (e.g., `| mv-expand`, `| union`).

## Steps

### 1. Define the AST node

In `src/adxlite/parser/ast_nodes.py`:

```python
@dataclass(frozen=True)
class MyNewOp(Operator):
    """Represents | my_new_op ..."""
    some_field: str
    other_field: tuple[Expr, ...]
```

### 2. Update the tokenizer (if needed)

In `src/adxlite/parser/tokenizer.py`:
- Add the operator keyword to the `KEYWORDS` set
- Hyphenated operators (like `project-away`) are handled automatically

### 3. Add parser logic

In `src/adxlite/parser/parser.py`:
- Import the new AST node
- Add a case in `_parse_operator()`:

```python
if keyword == "my-new-op":
    return self._parse_my_new_op()
```

### 4. Decide execution strategy

- **SQL-capable**: Translate in `src/adxlite/translator/translator.py`
- **Pandas-only**: Execute in `src/adxlite/engine/pandas_ops.py`

For SQL, add a case in `SqlTranslator._apply_operator()`:
```python
if isinstance(op, MyNewOp):
    return f"SELECT ... FROM ({source_sql}) AS _t ...", params
```

### 5. Update the planner

In `src/adxlite/engine/planner.py`, classify the operator's SQL-capability.

### 6. Write tests and update docs

- `tests/integration/` or `tests/unit/`
- `docs/reference/operators.md`
- `.github/instructions.md`

## Rules

- Each operator wraps previous pipeline as subquery: `SELECT ... FROM ({prev}) AS _t`
- Never string-interpolate user values — always parameterize
- Raise `KqlUnsupportedError` if truly unsupported
