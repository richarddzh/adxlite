# Skill: Debugging KQL Translation Issues

## When to Use

When a KQL query produces incorrect SQL, wrong results, or runtime errors.

## Diagnosis Steps

### 1. Inspect the token stream

```python
from adxlite.parser.tokenizer import Tokenizer
tokens = Tokenizer("logs | where x matches regex 'fail'").tokenize()
for t in tokens:
    print(f"  {t.type.name:12} {t.value!r}")
```

### 2. Inspect the AST

```python
from adxlite.parser import parse_kql
ast = parse_kql("logs | where x > 5 | take 10")
print(ast)
```

### 3. Inspect generated SQL

```python
from adxlite.parser import parse_kql
from adxlite.translator import SqlTranslator

ast = parse_kql("logs | where msg contains 'fail'")
translator = SqlTranslator()
sql, params = translator.translate(ast)
print(f"SQL: {sql}")
print(f"Params: {params}")
```

### 4. Run SQL directly against SQLite

Isolate whether the bug is in translation or execution.

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `IndexError: pop from empty list` | String op translating literal wrong | Build LIKE pattern directly |
| Wrong row count after `take \| where` | Missing nested subquery | Wrap in `SELECT * FROM (...) AS _t` |
| `no such column` | Unquoted special identifier | Use `[bracket]` quoting |
| `\w` becomes `w` in regex | Tokenizer escape handling | Unknown escapes preserve backslash |
| `matches regex` wrong | Full vs partial match | KQL uses `re.search` (partial) |
| `datetime(2024-01-02)` error | Not a function, it's a literal | Parser has `_finish_datetime_literal()` |

## Prevention

- Write tests BEFORE implementing (TDD)
- Always parameterize values with `?`
- Run `pytest tests/ -v` after every change
