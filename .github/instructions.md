# AdxLite - Copilot Instructions

## Overview

AdxLite is a local SQLite-based file database with a KQL interface. It ingests pandas DataFrames, stores them in SQLite, translates supported KQL operators into SQL plus SQLite UDFs, and falls back to pandas for operators such as `parse`.

It never connects to an external Kusto cluster.

## Current architecture

```text
src/adxlite/
├── __init__.py              # Public API exports
├── client.py                # Thin facade class
├── exceptions.py            # Exception hierarchy
├── parser/                  # Tokenizer, AST, recursive-descent parser
├── translator/              # SQL helpers, function registry, SQL translator
├── storage/                 # SQLite database, type mapping, UDFs
└── engine/                  # Planner, executor, pandas operators
```

Dependency direction:

```text
client -> engine -> translator + storage
engine -> parser
translator -> parser.ast_nodes + translator.sql_utils
storage -> exceptions
parser -> exceptions
```

## Key implementation rules

1. Use nested subqueries to preserve pipeline order.
2. Parameterize every literal with `?` placeholders.
3. Resolve `project-away` during planning from live schema.
4. Register SQLite UDFs exactly once per connection.
5. Store datetime columns as ISO-8601 text and restore known datetime columns on query.
6. Keep the engine local-only; never add remote connectivity.

## Supported surface

### Operators
- `where`, `project`, `project-away`, `extend`, `summarize`
- `take`, `limit`, `count`, `sort by`, `order by`, `top`, `distinct`, `parse`
- `.append TableName <| query`

### Functions
- Aggregation: `count`, `sum`, `avg`, `min`, `max`, `dcount`, `countif`, `sumif`, `avgif`
- String: `tolower`, `toupper`, `strlen`, `trim`, `substring`, `strcat`, `replace_string`, `reverse`, `countof`, `indexof`, `split`, URL/base64 helpers
- Math: `log`, `log2`, `log10`, `pow`, `sqrt`, `exp`, `ceiling`, `floor`, `sign`, `pi`, `round`, `abs`
- Datetime: `now`, `ago`, `bin`, `datetime_diff`, `format_datetime`, `datetime_add`
- Regex: `extract`, `matches regex`
- JSON: `parse_json`, `dynamic`, `extractjson`
- Conditional/conversion: `iif`, `iff`, `coalesce`, `isnull`, `isnotnull`, `isempty`, `isnotempty`, `tostring`, `toint`, `tolong`, `todouble`, `toreal`

### Unsupported
Raise `KqlUnsupportedError` for `join`, `union`, `mv-expand`, `mv-apply`, `render`, `let`, `invoke`, and `evaluate`.

## Testing

- Run `\.venv\Scripts\python.exe -m pytest tests\ -v`
- Keep tests split between unit and integration coverage.
- Prefer deterministic assertions with explicit `sort` before `take`.
- Use `:memory:` databases in tests unless file persistence is under test.

## Coding standards

- Public functions and classes need Google-style docstrings.
- Public APIs need type hints.
- Avoid circular imports.
- Use `quote_identifier()` for all SQL identifiers.
- Raise meaningful errors with context; never silently swallow failures.
