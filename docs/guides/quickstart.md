# Quickstart

This guide gets you from a fresh Python environment to a working AdxLite query in a few minutes. It assumes you know basic Python and pandas, but it does **not** assume prior KQL experience.

By the end of the guide you will know how to:

- install AdxLite into a virtual environment
- create an `AdxLiteClient`
- ingest a pandas DataFrame as a table
- run KQL queries and get pandas DataFrame results back
- choose between file-backed and in-memory databases
- use the client as a context manager

## What AdxLite does in one sentence

AdxLite stores tables in SQLite, accepts a subset of KQL as the query language, and returns results as pandas DataFrames.

## Step 1: create a virtual environment

On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
```

On macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## Step 2: install the package

Install from PyPI when consuming the library:

```bash
python -m pip install adxlite
```

Install from a local checkout when developing:

```bash
python -m pip install -e .[dev]
```

## Step 3: create some example data

AdxLite uses pandas DataFrames as both the ingestion format and the query output format.

```python
import pandas as pd

events = pd.DataFrame(
    {
        "user": ["ada", "alan", "grace", "ada"],
        "city": ["London", "London", "Arlington", "London"],
        "value": [10, 20, 30, 40],
        "ok": [True, True, False, True],
        "ts": pd.to_datetime([
            "2024-01-01T10:05:00",
            "2024-01-01T10:45:00",
            "2024-01-02T08:00:00",
            "2024-01-02T08:30:00",
        ]),
    }
)
```

## Step 4: create a client

The main API is `AdxLiteClient`.

```python
from adxlite import AdxLiteClient

client = AdxLiteClient(":memory:")
```

### Constructor parameter

| Parameter | Type | Description |
| --- | --- | --- |
| `database` | `str` | SQLite database path or `":memory:"` for an in-memory database |

### Return value

The constructor returns an `AdxLiteClient` instance that owns a SQLite connection and query execution engine.

### Notes

- `":memory:"` is best for tests, temporary analysis, and examples.
- a file path is best when you want the database contents to persist across sessions.
- each client instance manages one SQLite connection.

## Step 5: ingest the DataFrame

```python
client.ingest("Events", events)
```

The `ingest()` method creates or replaces a SQLite table named `Events`, infers the logical KQL schema from the DataFrame, and writes metadata used for later query result restoration.

### Ingestion parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `table_name` | `str` | Destination table name |
| `dataframe` | `pandas.DataFrame` | Data to write |
| `mode` | `Literal["replace", "append"]` | Replace the table or append to an existing schema |

### Return value

`ingest()` returns `None`. On success the table becomes immediately queryable.

## Step 6: run your first query

```python
result = client.query(
    """
    Events
    | where city == "London"
    | extend boosted = value + 5
    | project user, boosted, ts
    | sort by ts desc
    | take 2
    """
)

print(result)
```

Example result:

```text
   user  boosted                  ts
0   ada       45 2024-01-02 08:30:00
1  alan       25 2024-01-01 10:45:00
```

### Query parameter

| Parameter | Type | Description |
| --- | --- | --- |
| `kql` | `str` | A supported KQL statement or `.append` management command |

### Query return value

`query()` always returns a `pandas.DataFrame`.

- normal queries return the projected rows
- `count` returns a one-row DataFrame with a `Count` column
- `.append` returns an empty DataFrame after writing rows

## Understanding the first query

If you do not know KQL, read the pipeline from top to bottom:

1. `Events` chooses the source table.
2. `where city == "London"` filters rows.
3. `extend boosted = value + 5` adds a computed column.
4. `project user, boosted, ts` keeps only selected columns.
5. `sort by ts desc` orders the rows.
6. `take 2` limits the output.

This pipeline style is one of the main reasons KQL feels readable for analytical queries.

## More first-day examples

### Example: summarize by category

```python
client.query(
    """
    Events
    | summarize total=count(), max_value=max(value) by city
    | sort by total desc
    """
)
```

Use `summarize` when you need grouped aggregates.

### Example: case-insensitive equality

```python
client.query('Events | where user =~ "ADA" | project user, value')
```

`=~` performs case-insensitive equality. The regular `==` operator is case-sensitive.

### Example: datetime bucketing

```python
client.query(
    'Events | extend bucket = bin(ts, 1h) | summarize total=count() by bucket | sort by bucket asc'
)
```

`bin()` groups datetimes into fixed-width windows. In this project the timespan argument is written as a literal such as `1h` or `30m`.

### Example: regex extraction

```python
logs = pd.DataFrame(
    {
        "Message": [
            "user=ada action=login",
            "user=alan action=logout",
        ]
    }
)
client.ingest("Logs", logs)

client.query(
    'Logs | parse Message with "user=" user " action=" action | project user, action'
)
```

`parse` is handled by the hybrid execution path. SQL gets the input rows, then pandas extracts the capture groups.

## File-backed vs in-memory databases

You can choose either persistence model depending on your workflow.

| Option | Example | Best for | Persistence |
| --- | --- | --- | --- |
| In-memory | `AdxLiteClient(":memory:")` | tests, notebooks, temporary analysis | lasts only as long as the client/connection |
| File-backed | `AdxLiteClient("analytics.db")` | repeatable local analysis, application state, shared fixtures | stored in a SQLite file |

### Example: file-backed database

```python
with AdxLiteClient("analytics.db") as client:
    client.ingest("Events", events)
    london = client.query('Events | where city == "London"')
```

When you reopen `analytics.db` later, the tables remain available.

## Using the context manager

`AdxLiteClient` implements `__enter__` and `__exit__`, so you can let Python close the SQLite connection automatically.

```python
from adxlite import AdxLiteClient

with AdxLiteClient(":memory:") as client:
    client.ingest("Events", events)
    result = client.query("Events | count")
    print(result)
```

The context manager is recommended for scripts and applications because it makes connection cleanup explicit and predictable.

## Listing tables and inspecting schema

```python
with AdxLiteClient(":memory:") as client:
    client.ingest("Events", events)
    print(client.list_tables())
    print(client.get_schema("Events"))
```

Example output:

```python
["Events"]
{"user": "string", "city": "string", "value": "long", "ok": "bool", "ts": "datetime"}
```

These helpers are useful when you are building tooling on top of AdxLite or validating ingestion behavior in tests.

## Common mistakes for new users

### Forgetting that AdxLite supports a subset of KQL

AdxLite supports `let`, `union`, and `join`, but operators such as `mv-expand`, `mv-apply`, and `render` raise `KqlUnsupportedError`. Check [limitations](../reference/limitations.md) before assuming full Azure Data Explorer compatibility.

### Assuming the database is remote

AdxLite never connects to an external Kusto cluster. Every table must come from local ingestion.

### Appending with a mismatched schema

`append` ingestion requires the incoming DataFrame columns to match the existing schema order exactly. See [ingestion guide](ingestion.md) for details.

### Expecting `parse_json()` to return Python dictionaries

JSON values are stored and returned as JSON text representations, not automatically expanded Python objects in the result DataFrame.

## Where to go next

- Read [Ingestion guide](ingestion.md) for replace/append behavior, datetime detection, and schema rules.
- Read [Advanced queries](advanced-queries.md) for `parse`, regex, JSON, datetime, and `.append` examples.
- Read [API reference](../reference/api.md) for method signatures and exception handling.
- Read [Operators reference](../reference/operators.md) for exact operator semantics.
