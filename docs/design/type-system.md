# Type System

This document explains how AdxLite represents data types across its three execution layers: KQL, SQLite, and pandas. Understanding the type system is important because AdxLite intentionally tracks logical type metadata rather than relying only on SQLite storage affinity.

For ingestion behavior see [Ingestion guide](../guides/ingestion.md). For architecture context see [Architecture](architecture.md). For function-level details see [Functions reference](../reference/functions.md).

## Type system overview

AdxLite works with logical KQL-style types, physical SQLite storage types, and pandas runtime dtypes.

The same value may therefore have three relevant representations:

- a logical KQL type exposed by `get_schema()`
- a SQLite column storage type used on disk
- a pandas dtype or Python object representation seen in DataFrame results

## Supported logical types

The project documentation and schema metadata use the following logical types.

| Logical type | Meaning |
| --- | --- |
| `string` | Textual data |
| `int` | 32-bit style integer conceptually; see note below |
| `long` | Integer values used by current inference and most numeric whole-number operations |
| `real` | Floating-point numeric data |
| `bool` | Boolean data |
| `datetime` | Timestamp data stored as ISO-8601 text |
| `timespan` | Duration literals such as `1d` and `30m` used in expressions and functions |
| `dynamic` | JSON-like values represented as JSON text |

## Important note on `int` vs `long`

Current DataFrame inference maps pandas integer columns to `long`. The public language surface includes conversion functions such as `toint()` and `tolong()`, but schema inference does not currently distinguish a separate stored `int` type from `long`.

Practical implication:

- for table schemas produced by ingestion, expect integer columns to appear as `long`
- treat `int` in the language reference as a supported conversion target rather than a distinct inferred storage schema category

## Mapping between KQL, SQLite, and pandas

| Logical KQL type | SQLite storage type | Typical pandas/runtime form | Notes |
| --- | --- | --- | --- |
| `string` | `TEXT` | `object` / string-like values | Default fallback type for non-numeric, non-datetime columns |
| `long` | `INTEGER` | integer dtype or object depending on result shape | Used for inferred integer columns and count-like outputs |
| `real` | `REAL` | float dtype | Used for floats and many math function outputs |
| `bool` | `INTEGER` | pandas nullable boolean on restored schema columns | SQLite stores booleans using integer affinity |
| `datetime` | `TEXT` | `datetime64[ns]` when restored | Stored as ISO-8601 text, restored through metadata |
| `dynamic` | `TEXT` | usually object/string containing JSON text | JSON is not auto-expanded to nested Python structures in results |
| `timespan` | literal, not table column by default | string literal parsed by helpers | Used primarily in expression parsing and UDF evaluation |

## Type inference during ingestion

Type inference happens in `storage.kql_types.infer_column_type()`.

Current inference rules:

1. pandas datetime dtype -> `datetime`
2. pandas boolean dtype -> `bool`
3. pandas integer dtype -> `long`
4. pandas float dtype -> `real`
5. everything else -> `string`

This means object-dtype columns containing Python dictionaries or lists are **not** automatically inferred as `dynamic`; they fall back to `string` unless you pre-normalize them to JSON text intentionally.

## Storage normalization rules

After type inference, AdxLite normalizes values for SQLite storage.

### `datetime`

- converted with `pandas.to_datetime(..., errors="coerce")`
- each non-null value is stored as `value.isoformat()`
- null or invalid values become `None`

### `bool`

- non-null values are converted to `bool(value)`
- nulls remain `None`
- SQLite stores the values with integer affinity

### Other types

- values are passed through with missing values normalized to `None`

## Result restoration rules

When `Database.query_dataframe()` receives a `result_schema`, it restores result columns by logical type.

Current restoration behavior:

- `datetime` -> `pandas.to_datetime(series, errors="coerce")`
- `bool` -> `series.astype("boolean")`
- other types -> returned as-is from the DataFrame built from SQLite rows

Important implication:

Columns created by SQL expressions may only be restored if the planner inferred an appropriate logical type for them.

## Datetime handling in detail

Datetime behavior is one of the most important parts of the type system because SQLite has no dedicated datetime storage type.

### Storage representation

Datetimes are stored as ISO-8601 strings in `TEXT` columns.

Example stored values:

```text
2024-01-01T10:05:00
2024-01-02T08:30:00
2024-01-02T08:30:00.123456
```

### Why this works well

- readable during direct SQLite inspection
- easy to parse back into pandas timestamps
- stable for UDF-based datetime math
- compatible with lexical ordering when values are consistently normalized

### Comparison semantics

Datetime comparisons are typically executed on the ISO-8601 values or UDF-transformed results.

Examples:

```kql
Events | where ts >= datetime(2024-01-01)
Events | where ts between (datetime(2024-01-01) .. datetime(2024-01-31))
```

Because AdxLite uses normalized ISO strings, these comparisons behave predictably for typical timestamp forms produced by ingestion and datetime helpers.

### Datetime-producing helpers

The planner treats several functions as datetime-like outputs represented as strings in SQL and then restored where schema allows.

Functions in this category include:

- `now()`
- `ago(timespan)`
- `bin(datetime_value, timespan)`
- `datetime_add(timespan, datetime_value)`

`format_datetime()` is different: it deliberately produces a formatted string, not a datetime value.

### `datetime(...)` literals

AdxLite supports `datetime(...)` literals in the parser.

Examples:

```kql
datetime(2024-01-02)
datetime(2024-01-02T10:30:00)
datetime("2024-01-02T10:30:00")
```

The parser collects the literal content and stores it as a datetime-kind literal node. At translation time it becomes a bound parameter value.

### `now()` and `ago()`

- `now()` returns the current UTC timestamp as an ISO-8601 string
- `ago(1d)` subtracts a parsed timespan from the current UTC timestamp and returns an ISO-8601 string

These are implemented in the UDF layer, not by SQLite built-ins.

### `bin()`

`bin(datetime_value, timespan)` snaps a datetime down to a fixed boundary.

Example:

```kql
Events | extend hour_bucket = bin(ts, 1h)
```

If `ts` is `2024-01-01T10:45:30` and the bucket is `1h`, the result is `2024-01-01T10:00:00`.

### `datetime_diff()`

`datetime_diff(unit, left, right)` returns an integer difference measured in the requested unit.

Supported units currently include:

- `day`
- `hour`
- `minute`
- `second`
- `millisecond`

### `datetime_add()`

AdxLite supports a simplified signature:

```kql
datetime_add(timespan, value)
```

Example:

```kql
Events | extend next_hour = datetime_add(1h, ts)
```

This is narrower than some Kusto variants that split unit and amount.

## Timespan handling in detail

Timespans are not currently inferred as table column schemas by ingestion. Instead, they are recognized primarily as expression literals and UDF inputs.

### Supported literal formats

| Literal example | Meaning |
| --- | --- |
| `1d` | one day |
| `12h` | twelve hours |
| `30m` | thirty minutes |
| `5s` | five seconds |
| `100ms` | one hundred milliseconds |
| `1.5h` | one and a half hours |

### Parsing rules

The UDF layer parses timespans using a simple `<number><unit>` model.

Supported units:

- `d`
- `h`
- `m`
- `s`
- `ms`

Unsupported examples include:

- compound values such as `1h30m`
- week units such as `1w`
- month or year units such as `1mo` or `1y`

Use the simplest supported unit form and, when needed, convert compound durations to a single unit manually.

## Dynamic / JSON handling

AdxLite exposes `dynamic`, `parse_json`, and `extractjson`, but it currently represents dynamic data as JSON text rather than a nested in-memory object model.

### What `dynamic()` and `parse_json()` return

Both functions produce JSON text strings.

Examples:

```kql
Logs | extend payload_json = parse_json(payload)
Logs | extend payload_json = dynamic(payload)
```

If `payload` contains `{"count": 9}`, the resulting value is a JSON string such as `{"count": 9}`.

### What `extractjson()` returns

`extractjson(path, json_text)` extracts a JSON path from a JSON string.

Behavior:

- returns `None` if the JSON is invalid or the path is not found
- returns JSON text when the extracted value is a list or object
- returns string form when the extracted value is scalar

Example:

```kql
Logs | extend count = extractjson("$.count", payload)
```

The result is a string such as `"9"`, not an integer. If you need a numeric type, convert it explicitly:

```kql
Logs | extend count = toint(extractjson("$.count", payload))
```

## String and numeric coercion rules

AdxLite is intentionally pragmatic rather than enforcing a strict formal static type system.

### Common coercion patterns

- `tostring(x)` casts to text
- `toint(x)` / `tolong(x)` cast numeric text to integer when possible
- `todouble(x)` / `toreal(x)` cast numeric text to floating-point when possible
- arithmetic operators generally rely on SQLite or pandas numeric behavior
- string helpers convert inputs to strings as needed

### Null handling

Many helper functions return `None` when one or more required inputs are null. Examples include many UDF-backed functions such as `replace_string`, `sqrt`, or `extractjson` when parsing fails.

### Boolean handling

Boolean table columns are restored to pandas nullable boolean dtype when the result schema says the column is `bool`. Intermediate expression results may also behave as standard pandas boolean Series depending on execution path.

## Type inference in planner expressions

The planner infers result types for expressions so the engine can restore outputs sensibly.

Examples:

- comparison operators such as `==`, `contains`, `has`, and `matches regex` infer `bool`
- numeric functions such as `sqrt`, `log`, and `pow` infer `real`
- integer-style functions such as `toint`, `countof`, and `datetime_diff` infer `long`
- string-style functions such as `extract`, `replace_string`, and `format_datetime` infer `string`
- aggregate `count`, `countif`, and `dcount` infer `long`

This inferred schema is one reason query results can restore datetime or boolean columns accurately after SQL execution.

## Practical recommendations

- use explicit conversion functions when reading JSON scalars
- keep datetime columns as pandas datetime dtype before ingestion
- treat `dynamic` values as JSON text unless you explicitly deserialize them in Python
- prefer `long` as the mental model for integer table columns
- remember that type restoration happens after query execution, not during raw SQLite storage

## Related documents

- [Ingestion guide](../guides/ingestion.md)
- [Functions reference](../reference/functions.md)
- [Operators reference](../reference/operators.md)
- [Limitations](../reference/limitations.md)
