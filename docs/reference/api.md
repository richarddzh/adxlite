# Python API Reference

This document describes the public Python API of AdxLite. It covers the `AdxLiteClient` class, the exported exception hierarchy, and the parser entry point exposed through `adxlite.parser.parse_kql`.

For usage-oriented examples, see [Quickstart](../guides/quickstart.md) and [Ingestion guide](../guides/ingestion.md). For internal behavior, see [Architecture](../design/architecture.md).

## Public modules at a glance

| Module | Main public surface |
| --- | --- |
| `adxlite` | `AdxLiteClient` and exception classes |
| `adxlite.parser` | `parse_kql()` |

## `AdxLiteClient`

`AdxLiteClient` is the main user-facing API for local KQL queries over SQLite-backed data.

### Constructor

```python
AdxLiteClient(database: str = ":memory:")
```

### Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `database` | `str` | SQLite file path or `":memory:"` for an in-memory database |

### Returns

An `AdxLiteClient` instance.

### Example

```python
from adxlite import AdxLiteClient

client = AdxLiteClient("analytics.db")
```

### Notes

- the constructor opens the SQLite connection immediately
- UDFs are registered automatically
- metadata tables are created automatically if needed

## `ingest()`

```python
ingest(
    table_name: str,
    dataframe: pandas.DataFrame,
    mode: Literal["replace", "append"] = "replace",
) -> None
```

### Description

Ingests a pandas DataFrame into SQLite.

### Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `table_name` | `str` | Destination table name |
| `dataframe` | `pandas.DataFrame` | Source data to write |
| `mode` | `Literal["replace", "append"]` | Replace existing contents or append to an existing schema |

### Returns

`None`

### Example

```python
client.ingest("Events", df)
client.ingest("Events", new_rows, mode="append")
```

### Notes

- `replace` recreates the table and metadata
- `append` validates column names and order against the existing schema
- invalid append shape raises `SchemaError`

## `ingest_from_pandas()`

```python
ingest_from_pandas(
    table_name: str,
    dataframe: pandas.DataFrame,
    mode: Literal["replace", "append"] = "replace",
) -> None
```

### Description

Alias for `ingest()`.

### Parameters

Identical to `ingest()`.

### Returns

`None`

### Example

```python
client.ingest_from_pandas("Events", df)
```

### Notes

Use whichever method name reads better in your application code. The behavior is identical.

## `query()`

```python
query(kql: str) -> pandas.DataFrame
```

### Description

Executes a supported KQL query or `.append` command and returns a pandas DataFrame.

### Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `kql` | `str` | Query text or `.append` command |

### Returns

A `pandas.DataFrame`.

### Example

```python
result = client.query(
    """
    Events
    | where value >= 10
    | summarize total=count() by city
    | sort by total desc
    """
)
```

### Notes

- normal queries return the query result rows
- `.append` returns an empty DataFrame after appending the rows
- parse errors and unsupported-language errors are surfaced as typed exceptions

## `list_tables()`

```python
list_tables() -> list[str]
```

### Description

Returns the available user tables.

### Returns

A list of table names excluding internal metadata tables.

### Example

```python
print(client.list_tables())
```

## `get_schema()`

```python
get_schema(table_name: str) -> dict[str, str]
```

### Description

Returns the logical KQL schema for a table.

### Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `table_name` | `str` | Name of the table to inspect |

### Returns

A dictionary mapping column names to logical KQL type names.

### Example

```python
schema = client.get_schema("Events")
```

### Notes

- if the table does not exist, `TableNotFoundError` is raised
- types are logical types such as `string`, `long`, `bool`, and `datetime`

## `drop_table()`

```python
drop_table(table_name: str) -> None
```

### Description

Drops a user table and its metadata entry.

### Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `table_name` | `str` | Table to remove |

### Returns

`None`

### Example

```python
client.drop_table("TempResults")
```

### Notes

- if the table does not exist, `TableNotFoundError` is raised

## `close()`

```python
close() -> None
```

### Description

Closes the underlying SQLite connection.

### Returns

`None`

### Example

```python
client.close()
```

## Context manager methods

`AdxLiteClient` supports use in a `with` block.

### `__enter__()`

```python
__enter__() -> AdxLiteClient
```

Returns the client itself.

### `__exit__()`

```python
__exit__(exc_type: object, exc: object, tb: object) -> None
```

Closes the client.

### Example

```python
with AdxLiteClient(":memory:") as client:
    client.ingest("Events", df)
    print(client.query("Events | count"))
```

## Exception hierarchy

All public exceptions derive from `AdxLiteError`.

```text
AdxLiteError
├── KqlParseError
├── KqlUnsupportedError
├── TableNotFoundError
├── SchemaError
├── ExecutionError
└── TranslationError
```

## `AdxLiteError`

Base class for all AdxLite-specific failures.

Use this when you want to catch any AdxLite-originated error in one block.

```python
from adxlite import AdxLiteError

try:
    client.query("Users | join Other on id")
except AdxLiteError as exc:
    print(f"AdxLite failure: {exc}")
```

## `KqlParseError`

Raised when KQL text cannot be parsed.

Typical causes:

- malformed tokens
- unterminated strings or bracketed identifiers
- missing parentheses or malformed operator syntax

## `KqlUnsupportedError`

Raised when syntax is recognized but intentionally unsupported.

Typical causes:

- unsupported operators such as `mv-expand`, `mv-apply`, `render`, `invoke`, `evaluate`
- unsupported functions
- unsupported management commands other than `.append`
- function `let` (lambda definitions with parameters)

## `TableNotFoundError`

Raised when a referenced table does not exist.

Typical causes:

- querying a table before ingesting it
- dropping or inspecting a non-existent table

## `SchemaError`

Raised when schema metadata is invalid or inconsistent.

Most commonly encountered during append ingestion when the incoming DataFrame columns do not exactly match the stored schema.

## `ExecutionError`

Raised when SQLite execution fails.

Typical causes:

- low-level SQLite errors during query execution
- insertion failures during ingestion
- other runtime storage problems

## `TranslationError`

Raised when AST translation to SQL fails.

Typical causes:

- unsupported aggregate placement
- invalid function argument counts discovered during translation
- translation-only mismatches that occur after parsing but before execution

## Catching exceptions selectively

### Catch user-query problems

```python
from adxlite import KqlParseError, KqlUnsupportedError

try:
    client.query(user_query)
except (KqlParseError, KqlUnsupportedError) as exc:
    print(f"Query issue: {exc}")
```

### Catch storage problems separately

```python
from adxlite import ExecutionError, SchemaError, TableNotFoundError

try:
    client.ingest("Events", df, mode="append")
except SchemaError:
    print("Append schema mismatch")
except TableNotFoundError:
    print("Missing table")
except ExecutionError as exc:
    print(f"SQLite failed: {exc}")
```

## `parse_kql()` in `adxlite.parser`

AdxLite exposes the parser entry point from the `adxlite.parser` module.

```python
from adxlite.parser import parse_kql
```

### Signature

```python
parse_kql(text: str) -> Pipeline | AppendCommand
```

### Description

Parses supported KQL text into AST nodes.

### Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `text` | `str` | KQL statement to parse |

### Returns

One of:

- `Pipeline` for standard query pipelines
- `AppendCommand` for `.append` commands

### Example

```python
from adxlite.parser import parse_kql

ast = parse_kql("Users | where score >= 10 | take 5")
print(type(ast).__name__)
```

### Notes

- `parse_kql()` is useful for tooling, tests, and introspection
- it is exposed through `adxlite.parser`, not the top-level `adxlite` package namespace
- the returned AST node classes live in `adxlite.parser.ast_nodes`

## Typical lifecycle example

```python
import pandas as pd
from adxlite import AdxLiteClient

frame = pd.DataFrame(
    {
        "user": ["ada", "alan"],
        "value": [10, 20],
    }
)

with AdxLiteClient(":memory:") as client:
    client.ingest("Events", frame)
    print(client.list_tables())
    print(client.get_schema("Events"))
    result = client.query("Events | summarize total=count(), max_value=max(value)")
    print(result)
```

---

# adxpandas API Reference

The `adxpandas` package provides pure-pandas KQL query execution — no SQLite or external databases required. It works directly on pandas DataFrames in memory.

## Public modules at a glance

| Module | Main public surface |
| --- | --- |
| `adxpandas` | `AdxPandasClient`, `Wrap`, `RenderResult` |
| `adxpandas.parser` | `parse_kql()` |
| `adxpandas.magic` | Jupyter `%kql` / `%%kql` magic |
| `adxpandas.render` | `RenderResult`, `render()` |
| `adxpandas.wrap` | `Wrap` |

## `AdxPandasClient`

The multi-table KQL client that executes queries against named DataFrames.

### Constructor

```python
AdxPandasClient()
```

Creates a client instance with no tables registered.

### `register_table()`

```python
register_table(name: str, df: pandas.DataFrame) -> None
```

Registers a DataFrame as a named table that can be referenced in KQL queries.

### `query()`

```python
query(kql: str) -> pandas.DataFrame
```

Executes a KQL query against registered tables and returns a DataFrame.

### Example

```python
from adxpandas import AdxPandasClient
import pandas as pd

client = AdxPandasClient()
client.register_table("Events", pd.DataFrame({"city": ["A", "B"], "score": [10, 20]}))
result = client.query("Events | where score > 15")
```

## `Wrap`

A single-DataFrame quick-query interface with method chaining. Ideal for interactive exploration.

### Constructor

```python
Wrap(df: pandas.DataFrame)
```

### Properties

| Property | Type | Description |
| --- | --- | --- |
| `df` | `pandas.DataFrame` | The underlying DataFrame |

### `execute()`

```python
execute(query: str) -> Wrap | RenderResult
```

Executes a KQL query using `self` as the table name. Returns `Wrap` for chaining, or `RenderResult` if the query ends with a `render` operator.

### Chaining Methods

All chaining methods return a new `Wrap` instance:

| Method | KQL equivalent | Example |
| --- | --- | --- |
| `where(condition)` | `\| where ...` | `w.where("x > 10")` |
| `project(*cols)` | `\| project ...` | `w.project("name", "age")` |
| `project_away(*cols)` | `\| project-away ...` | `w.project_away("temp")` |
| `extend(*exprs)` | `\| extend ...` | `w.extend("y = x * 2")` |
| `summarize(agg, by=)` | `\| summarize ...` | `w.summarize("count()", by="city")` |
| `sort(by)` | `\| sort by ...` | `w.sort("score desc")` |
| `order(by)` | `\| order by ...` | Alias for `sort()` |
| `take(n)` | `\| take n` | `w.take(10)` |
| `limit(n)` | `\| limit n` | Alias for `take()` |
| `top(n, by)` | `\| top n by ...` | `w.top(5, "score desc")` |
| `count()` | `\| count` | `w.count()` |
| `distinct(*cols)` | `\| distinct ...` | `w.distinct("city")` |

### `render()`

```python
render(visualization: str = "linechart", **kwargs) -> RenderResult
```

Terminal method — creates a chart from the current DataFrame.

**kwargs:** `xcolumn`, `ycolumns` (str or tuple), `title`

### Example

```python
from adxpandas import Wrap
import pandas as pd

df = pd.DataFrame({"city": ["NYC", "LA", "SF"], "pop": [8, 4, 1]})
w = Wrap(df)

# Method chaining
result = w.where("pop > 2").sort("pop desc")
print(result.df)

# Full KQL query
result = w.execute("self | summarize total=sum(pop)")

# Render chart
chart = w.render("barchart", xcolumn="city", title="Population")
chart.show()
```

### Notes

- Uses `self` as the implicit table name
- Each method returns a **new** Wrap — the original is never mutated
- `__len__()` returns row count; `_repr_html_()` renders in Jupyter

## `RenderResult`

Result of a query that ends with a `render` operator. Displays charts in Jupyter notebooks.

### Fields

| Field | Type | Description |
| --- | --- | --- |
| `df` | `pandas.DataFrame` | The query result data |
| `render_op` | `RenderOp` | The render specification |

### Properties

| Property | Type | Description |
| --- | --- | --- |
| `figure` | `matplotlib.Figure` | Lazily-created matplotlib figure |

### `_repr_html_()`

Returns a base64-encoded PNG `<img>` tag for Jupyter display.

### `show()`

Calls `matplotlib.pyplot.show()` to display the chart interactively.

### Example

```python
from adxpandas import Wrap

w = Wrap(df)
result = w.execute("self | summarize avg(score) by city | render barchart")
result.show()  # Opens matplotlib window
```

### Notes

- Requires `matplotlib` (`pip install adxpandas[notebook]`)
- The figure is created lazily on first access
- Supported chart types: `timechart`, `linechart`, `barchart`, `columnchart`, `piechart`, `areachart`, `table`

## Jupyter Magic (`%kql`)

The `adxpandas.magic` module provides `%kql` and `%%kql` magic commands for Jupyter notebooks.

### Setup

```python
import adxpandas.magic
```

This registers the magic commands if IPython is available.

### Line Magic

```python
%kql df | where x > 5 | take 10
```

Executes a single-line KQL query. The first identifier is resolved from local/global namespace as a DataFrame or Wrap.

### Cell Magic

```python
%%kql df
| where x > 5
| summarize count() by city
| render barchart
```

The first line after `%%kql` specifies the table name. Subsequent lines form the query body.

### Notes

- Scans `locals()` and IPython's `user_ns` for DataFrames and Wraps
- Returns `Wrap` or `RenderResult` depending on whether the query has a `render` clause
- Requires IPython/Jupyter environment

## adxpandas Exception

### `AdxPandasError`

Base exception for adxpandas operations.

```python
from adxpandas import AdxPandasError
```

## Related documents

- [Quickstart](../guides/quickstart.md)
- [Ingestion guide](../guides/ingestion.md)
- [Architecture](../design/architecture.md)
- [Limitations](limitations.md)
