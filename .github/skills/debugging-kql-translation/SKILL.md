---
name: "debugging-kql-translation"
description: "Use when debugging KQL query failures, parse errors, or runtime exceptions. Covers token inspection, AST debugging, and known issues."
---

# Skill: Debugging KQL Translation Issues

## When to Use

When a KQL query produces incorrect results, parse errors, or runtime errors.

## Diagnosis Steps

### 1. Inspect the token stream

```python
from adxpandas.parser.tokenizer import Tokenizer
tokens = list(Tokenizer("T | where x !has 'test'").tokenize())
for t in tokens:
    print(f"  {t.type.name:12} {t.value!r}")
```

### 2. Inspect the AST

```python
from adxpandas.parser.tokenizer import Tokenizer
from adxpandas.parser.parser import Parser
tokens = Tokenizer("T | summarize count() by bucket = x % 2").tokenize()
ast = Parser(tokens).parse()
for op in ast.operators:
    print(type(op).__name__, vars(op))
```

### 3. Test execution directly

```python
from adxpandas import AdxPandasClient
import pandas as pd
client = AdxPandasClient({"T": pd.DataFrame({"x": [1, 2, 3]})})
result = client.query("T | where x > 1")
print(result)
```

### 4. For adxlite, inspect generated SQL

```python
from adxpandas.parser.tokenizer import Tokenizer
from adxpandas.parser.parser import Parser
from adxlite.translator import SqlTranslator

tokens = Tokenizer("T | where msg contains 'fail'").tokenize()
ast = Parser(tokens).parse()
translator = SqlTranslator()
sql, params = translator.translate(ast)
print(f"SQL: {sql}")
print(f"Params: {params}")
```

## Common Issues and Known Fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `!in`/`!has` parse error | Tokenizer didn't handle `!` prefix | Tokenizer emits `not` keyword + next keyword |
| `!has`/`!contains` parse error | Parser missing negated string ops | Added UnaryOp("not", BinaryOp(...)) |
| `iif("literal")` crashes | Scalar string has no `.where()` | Wrap scalar args in `pd.Series` |
| `summarize by alias=expr` wrong | `=` parsed as `==` comparison | Use `_parse_named_expr_list()` for by-clause |
| `summarize by x` (no agg) error | `by` consumed as identifier | Check for `by` keyword BEFORE parsing aggs |
| `split(x, "")` ValueError | Python `str.split("")` disallowed | Special-case: return `list(text)` |
| `tostring(NaN)` → `"nan"` | pandas 2.x behavior | Tests must not assume coalesce catches this |
| `strlen(None)` → `4` on CI | pandas 2.x: `None.astype(str)` → `"None"` | Don't test null-propagation in string funcs |
| Wrong row count after `take | where` | Missing nested subquery | Wrap in `SELECT * FROM (...) AS _t` |

## Prevention

- Write tests BEFORE implementing (TDD)
- Always test on CI (Python 3.10 + pandas 2.x) not just locally
- Run `pytest tests/ --tb=short` after every change in BOTH packages
- For parser changes, test both adxpandas and adxlite since they share the parser
