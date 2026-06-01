# Data Ingestion Guide

This guide explains how AdxLite turns pandas DataFrames into queryable SQLite tables. It covers the `ingest_from_pandas()` API, the relationship between `replace` and `append` modes, how schemas are inferred and validated, and what to watch for when loading large datasets.

If you are new to the project, read [Quickstart](quickstart.md) first. For deeper details on logical types, see [Type system](../design/type-system.md). For full API signatures, see [API reference](../reference/api.md).

## Ingestion model at a glance

AdxLite ingestion is intentionally simple:

1. create or open an `AdxLiteClient`
2. pass a pandas DataFrame to `ingest()` or `ingest_from_pandas()`
3. AdxLite infers the logical KQL schema
4. values are normalized for SQLite storage
5. a SQLite user table and a metadata entry are created or updated

The result is a table that can be queried immediately with KQL.

## Public ingestion APIs

AdxLite exposes two ingestion entry points on `AdxLiteClient`.

### `ingest()`

```python
client.ingest(table_name, dataframe, mode="replace")
```

### `ingest_from_pandas()`

```python
client.ingest_from_pandas(table_name, dataframe, mode="replace")
```

`ingest_from_pandas()` is an alias for `ingest()`. Use either name based on which feels clearer in your codebase. Some teams prefer `ingest_from_pandas()` because it makes the source format explicit; others prefer the shorter `ingest()` call.

## Parameter reference

| Parameter | Type | Description |
| --- | --- | --- |
| `table_name` | `str` | Name of the destination table in SQLite |
| `dataframe` | `pandas.DataFrame` | Source rows to write |
| `mode` | `Literal["replace", "append"]` | Whether to recreate the table or add rows to an existing table |

### Return value

Both ingestion methods return `None`.

### Exceptions you may see

| Exception | When it can happen |
| --- | --- |
| `ValueError` | `mode` is not `replace` or `append` |
| `SchemaError` | `append` mode receives columns that do not exactly match the existing schema |
| `ExecutionError` | SQLite fails while creating or writing the table |

## Replace mode

`replace` is the default mode.

```python
client.ingest("Events", df, mode="replace")
```

### Replace semantics

When you use `replace`:

- any existing SQLite table with that name is dropped
- the metadata entry for that table is cleared
- a new table is created from the DataFrame schema
- rows from the incoming DataFrame are inserted
- the logical schema becomes exactly the schema inferred from the new DataFrame

### When to use replace

Use `replace` when:

- loading a table for the first time
- rebuilding a table from scratch in a test or notebook
- changing the schema intentionally
- refreshing a full dataset from an authoritative source

### Example

```python
client.ingest(
    "Users",
    pd.DataFrame(
        {
            "name": ["Ada", "Alan"],
            "score": [10, 20],
        }
    ),
    mode="replace",
)
```

## Append mode

`append` adds rows to an existing table.

```python
client.ingest("Events", more_rows, mode="append")
```

### Append semantics

When you use `append`:

- the target table must already exist, unless the table is missing and AdxLite falls back to creating it through the same logic as replace mode
- the incoming DataFrame column names and order must exactly match the existing schema order
- the incoming rows are normalized using the stored logical schema
- the table definition and metadata are preserved

### Schema rule that matters most

Append validation is strict about column order and names.

This will succeed:

```python
base = pd.DataFrame({"name": ["Ada"], "score": [10]})
more = pd.DataFrame({"name": ["Alan"], "score": [20]})

client.ingest("Users", base)
client.ingest("Users", more, mode="append")
```

This will fail because the columns are reordered:

```python
bad = pd.DataFrame({"score": [30], "name": ["Grace"]})
client.ingest("Users", bad, mode="append")  # raises SchemaError
```

### Why append is strict

Strict append validation prevents a subtle class of bugs where values are written into the wrong columns or where one ingestion call quietly changes the table shape for later queries.

## DataFrame type mapping

AdxLite infers a logical KQL schema from the incoming DataFrame.

| pandas dtype pattern | Logical KQL type | SQLite type |
| --- | --- | --- |
| datetime-like | `datetime` | `TEXT` |
| boolean | `bool` | `INTEGER` |
| integer | `long` | `INTEGER` |
| float | `real` | `REAL` |
| everything else | `string` | `TEXT` |

### Important practical notes

- object-dtype columns are treated as `string` by default
- integer columns become `long`, not a separate stored `int` type
- datetime columns are stored as ISO-8601 text and restored later based on metadata
- booleans use SQLite integer affinity but are restored to pandas nullable booleans when schema information is available

## DateTime column detection

Datetime support works best when your DataFrame columns already use pandas datetime dtype.

### Recommended pattern

```python
df["ts"] = pd.to_datetime(df["ts"])
client.ingest("Events", df)
```

### What happens internally

1. AdxLite detects datetime dtype through pandas type checks.
2. Each value is converted to ISO-8601 text with `isoformat()`.
3. SQLite stores the values in a `TEXT` column.
4. The metadata table records the logical type as `datetime`.
5. Query results for that column are restored with `pandas.to_datetime()`.

### Why pre-normalizing matters

If a timestamp column is left as plain object strings, AdxLite will infer `string`, not `datetime`. The values may still be queryable as text, but you lose datetime restoration and explicit schema typing.

## Schema management and metadata

AdxLite stores logical schema information in the internal `__adxlite_columns` metadata table.

### What metadata is tracked

| Field | Description |
| --- | --- |
| `table_name` | The user table name |
| `column_name` | The logical column name |
| `ordinal` | The original column position |
| `kql_type` | The inferred logical KQL type |

### Why metadata matters

Metadata is used for:

- `get_schema()` output
- append-mode validation
- result restoration for datetime and bool columns
- planner schema inference as queries flow through operators

### Inspecting schema after ingestion

```python
schema = client.get_schema("Events")
print(schema)
```

Example output:

```python
{"user": "string", "value": "long", "ok": "bool", "ts": "datetime"}
```

## Example: mixed-type ingestion

```python
import pandas as pd
from adxlite import AdxLiteClient

frame = pd.DataFrame(
    {
        "user": ["ada", "alan"],
        "active": [True, False],
        "count": [3, 5],
        "ratio": [0.5, 1.25],
        "ts": pd.to_datetime(["2024-01-01", "2024-01-02"]),
        "payload": ['{"count": 3}', '{"count": 5}'],
    }
)

with AdxLiteClient(":memory:") as client:
    client.ingest_from_pandas("Events", frame)
    print(client.get_schema("Events"))
```

Expected schema shape:

```python
{
    "user": "string",
    "active": "bool",
    "count": "long",
    "ratio": "real",
    "ts": "datetime",
    "payload": "string",
}
```

Note that `payload` remains `string` even though it contains JSON text.

## Example: creating an empty table

You can ingest an empty DataFrame to define a table schema before appending rows later.

```python
empty = pd.DataFrame(
    {
        "name": pd.Series(dtype="string"),
        "score": pd.Series(dtype="int64"),
        "ts": pd.Series(dtype="datetime64[ns]"),
    }
)

client.ingest("Users", empty)
```

This is useful for tests and for `.append` workflows that need a destination table before the first data movement query.

## Example: append workflow

```python
base = pd.DataFrame(
    {
        "name": ["Ada"],
        "score": [10],
        "ts": pd.to_datetime(["2024-01-01T10:00:00"]),
    }
)

more = pd.DataFrame(
    {
        "name": ["Alan", "Grace"],
        "score": [20, 30],
        "ts": pd.to_datetime(["2024-01-01T11:00:00", "2024-01-01T12:00:00"]),
    }
)

with AdxLiteClient(":memory:") as client:
    client.ingest("Users", base)
    client.ingest("Users", more, mode="append")
    print(client.query("Users | sort by ts asc"))
```

## Large dataset considerations

AdxLite is appropriate for local analytics, tests, notebooks, and modest embedded workloads. It is not designed as a distributed ingestion system.

### What to keep in mind

- ingestion copies data from pandas into SQLite, so very large frames incur serialization cost
- replace mode recreates the table, which is simple but can be expensive for large reloads
- append mode avoids a full rebuild, but still validates schema and inserts row by row through SQLite executemany
- object-dtype columns may be slower and less memory-efficient than well-typed numeric or datetime columns

### Practical tips

- convert columns to stable numeric, boolean, or datetime dtypes before ingestion
- append in batches when you are loading incrementally
- prefer file-backed databases for repeatable large local workflows instead of rebuilding everything each process run
- keep JSON payload columns as text unless you truly need them queried

## Common ingestion pitfalls

### Pitfall: forgetting to normalize datetimes

If you pass raw strings instead of pandas datetime dtype, the schema becomes `string`.

### Pitfall: assuming append will reorder columns

It will not. Reorder your DataFrame columns explicitly before calling `append` mode.

### Pitfall: expecting nested Python objects in dynamic columns

AdxLite stores and returns JSON as text by default. If you need nested Python objects, deserialize after the query in your own Python code.

### Pitfall: using unsupported append modes

Only `replace` and `append` are valid modes.

## Ingestion and query lifecycle together

A common production-style workflow looks like this:

1. ingest or refresh a source table from a DataFrame
2. run KQL pipelines for reporting or filtering
3. optionally materialize derived results with `.append`
4. inspect schema or list tables for observability and validation

That lifecycle is why the ingestion model is intentionally conservative about schema consistency.

## Related documents

- [Quickstart](quickstart.md)
- [Advanced queries](advanced-queries.md)
- [Type system](../design/type-system.md)
- [API reference](../reference/api.md)
