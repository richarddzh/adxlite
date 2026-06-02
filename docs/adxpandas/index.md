# adxpandas

**adxpandas** is a standalone sub-module that executes Kusto Query Language (KQL) queries directly over one or more pandas DataFrames — no database required.

## When to use adxpandas vs adxlite

| Feature | adxpandas | adxlite |
|---------|-----------|---------|
| KQL over DataFrames | ✅ | ✅ (via SQLite) |
| No database dependency | ✅ | ❌ (requires SQLite) |
| Persistent storage | ❌ | ✅ |
| SQL-accelerated queries | ❌ | ✅ |
| `.append` command | ❌ | ✅ |
| Type-aware storage | ❌ | ✅ |

Use **adxpandas** when you want to query DataFrames in-memory without any persistence layer. Use **adxlite** when you need persistent storage, SQL acceleration, or data ingestion workflows.

## Installation

```bash
pip install adxpandas
```

## Quick Start

```python
import pandas as pd
from adxpandas import AdxPandasClient

users = pd.DataFrame({
    "name": ["Ada", "Alan", "Grace"],
    "city": ["London", "London", "Arlington"],
    "score": [10, 20, 30],
})

client = AdxPandasClient({"Users": users})
result = client.query('Users | where city == "London" | project name, score')
print(result)
```

## API Reference

### `AdxPandasClient`

```python
class AdxPandasClient:
    def __init__(self, tables: dict[str, pd.DataFrame] | None = None) -> None: ...
    def add_table(self, name: str, dataframe: pd.DataFrame) -> None: ...
    def remove_table(self, name: str) -> None: ...
    def query(self, kql: str) -> pd.DataFrame: ...
    def list_tables(self) -> list[str]: ...
```

### Supported Operators

All operators supported by adxlite are supported in adxpandas:

- `where` — filter rows
- `project` — select/rename columns
- `project-away` — remove columns
- `extend` — add computed columns
- `summarize` — aggregate with grouping
- `sort by` / `order by` — sort rows
- `top` — top N by column
- `take` / `limit` — limit row count
- `distinct` — deduplicate
- `count` — row count
- `parse` — extract fields from strings
- `join` — join two tables
- `union` — combine tables

### Supported Functions

All scalar and aggregate functions supported by adxlite are available in adxpandas. See [Functions Reference](../reference/functions.md) for the full list.

### `let` Statements

Both scalar and tabular `let` bindings are supported:

```kql
let threshold = 100;
let active_users = Users | where last_login > ago(7d);
active_users | where score > threshold | project name, score
```

### Unsupported Features

- `.append` command (use adxlite for storage operations)
- Persistent storage / ingestion
- SQLite-specific features

## Architecture

adxpandas consists of:

- **Parser** — shared KQL parser (tokenizer, AST, recursive descent parser)
- **Functions** — pure-Python implementations of KQL scalar functions
- **Engine** — pandas-native execution of KQL operators
  - `PandasOperatorExecutor` — applies individual operators to DataFrames
  - `PandasExecutionEngine` — orchestrates full query execution including `let` bindings, unions, and joins
