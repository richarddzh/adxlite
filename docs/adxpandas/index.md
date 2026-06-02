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
- `render` — chart visualization (timechart, barchart, columnchart, piechart, linechart, areachart)

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

## Wrap: Single-DataFrame Quick Query

The `Wrap` class provides a fluent API for querying a single DataFrame:

```python
from adxpandas import Wrap

w = Wrap(df)

# Execute KQL query (use 'self' as the table name)
result = w.execute('self | where city == "London" | project name, score')
print(result.df)

# Method chaining
w.where('score > 10').sort('score desc').take(5).df

# Chart rendering
w.summarize("count()", by="city").render("barchart")
```

### Wrap API

```python
class Wrap:
    def __init__(self, df: pd.DataFrame) -> None: ...

    @property
    def df(self) -> pd.DataFrame: ...

    def execute(self, query: str) -> Wrap | RenderResult: ...

    # Chaining methods (all return Wrap)
    def where(self, condition: str) -> Wrap: ...
    def project(self, *columns: str) -> Wrap: ...
    def project_away(self, *columns: str) -> Wrap: ...
    def extend(self, *expressions: str) -> Wrap: ...
    def summarize(self, aggregations: str, by: str | None = None) -> Wrap: ...
    def sort(self, by: str) -> Wrap: ...
    def take(self, n: int) -> Wrap: ...
    def top(self, n: int, by: str) -> Wrap: ...
    def count(self) -> Wrap: ...
    def distinct(self, *columns: str) -> Wrap: ...

    # Terminal method (returns RenderResult)
    def render(self, visualization: str, **kwargs) -> RenderResult: ...
```

## Jupyter Magic

The `%kql` magic enables interactive KQL queries in Jupyter notebooks:

```python
import adxpandas.magic  # registers %kql and %%kql

# Line magic
%kql df | where score > 10 | take 5

# Cell magic
%%kql
df
| where city == "London"
| summarize avg(score) by city

# Capture result
result = %kql df | where score > 10
```

**How it works:**

- Scans local and global namespace for DataFrames and Wraps
- Variable names become table names in the query
- Returns `Wrap` (for data) or `RenderResult` (if query ends with render)
- Requires IPython: `pip install adxpandas[notebook]`

## Render: Chart Visualization

The `render` operator produces charts from query results:

```kql
T | summarize count() by city | render barchart
T | summarize avg(score) by bin(ts, 1h) | render timechart
T | ... | render columnchart with (xcolumn=name, title="Scores")
```

### Supported Visualizations

| Type | Description |
|------|-------------|
| `timechart` | Line chart (time series) |
| `linechart` | General line chart |
| `barchart` | Horizontal bar chart |
| `columnchart` | Vertical bar chart |
| `piechart` | Pie chart |
| `areachart` | Filled area chart |
| `table` | Table figure |

### RenderResult

```python
class RenderResult:
    df: pd.DataFrame         # The underlying data
    render_op: RenderOp      # The render specification
    figure: matplotlib.Figure  # The chart (lazily created)

    def _repr_html_(self) -> str: ...  # Jupyter display
    def show(self) -> None: ...        # plt.show()
```

### Requirements

- Requires matplotlib: `pip install adxpandas[notebook]`
- `AdxPandasClient.query()` ignores render (always returns DataFrame)
- Wrap and magic handle render → RenderResult conversion

## Architecture

adxpandas consists of:

- **Parser** — shared KQL parser (tokenizer, AST, recursive descent parser)
- **Functions** — pure-Python implementations of KQL scalar functions
- **Engine** — pandas-native execution of KQL operators
  - `PandasOperatorExecutor` — applies individual operators to DataFrames
  - `PandasExecutionEngine` — orchestrates full query execution including `let` bindings, unions, and joins

## Acknowledgments

Some functionality in adxpandas was inspired by and references [KustoPandas](https://github.com/js850/KustoPandas). We thank the KustoPandas authors for their pioneering work on KQL-over-pandas execution.
