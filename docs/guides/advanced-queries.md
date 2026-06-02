# Advanced Query Patterns

This guide collects practical query patterns for the more expressive parts of AdxLite. It is aimed at users who already know the basics of `where`, `project`, and `summarize` and want to compose richer pipelines.

If you need operator syntax details, see [Operators reference](../reference/operators.md). If you need function signatures, see [Functions reference](../reference/functions.md). If you are new to AdxLite, read [Quickstart](quickstart.md) first.

## What “advanced” means in AdxLite

In this project, advanced queries usually involve one or more of the following:

- multiple pipeline stages chained together
- computed columns with scalar functions
- `parse` for structured extraction from text
- datetime bucketing or relative-time filtering
- regex matching and extraction
- JSON parsing and extraction
- grouped aggregation
- conditional expressions
- `let` bindings for named sub-expressions
- `union` for combining tables with compatible schemas
- `join` for correlating tables by key columns
- `.append` for materializing query results locally

## Pattern: build pipelines incrementally

A good KQL habit is to build a query in readable stages.

Example:

```kql
Events
| where city == "London"
| extend user_upper = toupper(user), bucket = bin(ts, 1h)
| summarize total=count(), max_value=max(value) by bucket, user_upper
| sort by bucket asc, user_upper asc
```

Why this pattern works well:

- each stage has one job
- debugging is easier because you can stop after any stage and inspect results
- it mirrors the nested-subquery execution model described in [Architecture](../design/architecture.md)

## Pattern: chain filtering before expensive transformations

Even though AdxLite is local, you still benefit from reducing the row set early.

Prefer:

```kql
Logs
| where Message matches regex "error|warn"
| parse Message with "user=" user " action=" action
| project user, action
```

Over:

```kql
Logs
| parse Message with "user=" user " action=" action
| where action == "login"
```

The first form lets SQLite do more work before the pandas-only `parse` stage begins.

## The `parse` operator

`parse` extracts columns from a source expression using a pattern composed of literals, wildcard skips, and capture names.

### Basic syntax

```kql
Table | parse SourceColumn with <pattern>
```

### Pattern parts

| Pattern part | Meaning |
| --- | --- |
| string literal | Match this exact text |
| `*` | Skip any matching text without capturing it |
| bare identifier | Capture the matching text into a new column |

### Example: simple capture

```kql
Logs
| parse Message with "user=" user " action=" action
| project user, action
```

If `Message` is `user=ada action=login`, the result columns become `user = "ada"` and `action = "login"`.

### Example: skip uninterested text

```kql
Logs
| parse Message with "user=" user * "status=" status
| project user, status
```

Use `*` when you know a message contains text between fields but you do not want to capture it.

### Example: parse a payload tail

```kql
Logs
| parse Message with "user=" user " action=" action " payload=" payload
| project user, action, payload
```

This is common when you want to extract a JSON payload and then query inside it with `extractjson()`.

### Notes on parse behavior

- `parse` currently runs in pandas, not in SQLite SQL
- captures are added as string columns
- the generated regex uses non-greedy matching when more captures follow and greedy matching near the end of the pattern
- the entire parse regex is anchored from start to end of the source string

## DateTime query patterns

Datetime support is a major strength of AdxLite's local analytics model.

## Pattern: filter using `ago()`

```kql
Events
| where ts >= ago(1d)
| sort by ts desc
```

Use this to find recent rows relative to the current UTC time.

## Pattern: use explicit datetime literals

```kql
Events
| where ts between (datetime(2024-01-01) .. datetime(2024-01-31))
```

This is useful for repeatable tests and deterministic reporting windows.

## Pattern: bucket timestamps with `bin()`

```kql
Events
| extend hour_bucket = bin(ts, 1h)
| summarize total=count() by hour_bucket
| sort by hour_bucket asc
```

`bin()` rounds timestamps down to the nearest bucket boundary.

## Pattern: compare timestamps with `datetime_diff()`

```kql
Events
| extend hours_from_now = datetime_diff("hour", now(), ts)
| project user, ts, hours_from_now
```

The function returns an integer count in the requested unit.

## Pattern: add durations with `datetime_add()`

```kql
Events
| extend next_retry = datetime_add(30m, ts)
| project ts, next_retry
```

AdxLite uses a simplified signature: `datetime_add(timespan, value)`.

## Regex matching and extraction

Regex support appears in two places:

- `matches regex` operator for predicates
- `extract()` function for capture extraction

## Pattern: partial-match filtering

```kql
Logs
| where Message matches regex "error|warning"
| project Message
```

Important note: AdxLite uses **partial-match** semantics. The pattern can match anywhere in the string.

## Pattern: pull a capture group with `extract()`

```kql
Logs
| extend user = extract("user=(\w+)", 1, Message)
| project user, Message
```

This returns the selected regex group as a string or null if the pattern does not match.

## JSON parsing and extraction

AdxLite represents JSON-oriented values as text, so JSON workflows typically combine `parse`, `parse_json`, `dynamic`, and `extractjson`.

## Pattern: keep JSON payload as text but extract a field

```kql
Logs
| parse Message with "payload=" payload
| extend count = extractjson("$.count", payload)
| project payload, count
```

`extractjson()` returns string values for scalar JSON leaves. Convert them if you need numeric behavior.

## Pattern: convert extracted JSON field to an integer

```kql
Logs
| parse Message with "payload=" payload
| extend count = toint(extractjson("$.count", payload))
| where count >= 10
```

## Pattern: normalize JSON text first

```kql
Logs
| extend payload_json = parse_json(payload)
| extend first_value = extractjson("$.items[0]", payload_json)
| project payload_json, first_value
```

`dynamic(payload)` is an alias for `parse_json(payload)` in AdxLite's current implementation.

## Aggregation with grouping

Grouped aggregation is one of the main reasons to use KQL pipelines.

## Pattern: count and max by category

```kql
Events
| summarize total=count(), max_value=max(value) by city
| sort by total desc
```

## Pattern: distinct count by group

```kql
Events
| summarize users=dcount(user) by city
| sort by users desc
```

## Pattern: conditional aggregation

```kql
Events
| summarize ok_rows=countif(ok), ok_value=sumif(value, ok), avg_ok=avgif(value, ok) by city
```

These functions let you calculate metrics for subsets of each group without pre-filtering the entire table.

## Pattern: aggregate after bucketing time

```kql
Events
| extend bucket = bin(ts, 1h)
| summarize total=count(), avg_value=avg(value) by bucket
| sort by bucket asc
```

This is a classic local time-series rollup pattern.

## Conditional expressions

Use `iif()` or `iff()` to branch inside projections or computed columns.

## Pattern: classify rows

```kql
Events
| extend value_band = iif(value >= 20, "high", "low")
| project user, value, value_band
```

## Pattern: fill nulls with `coalesce()`

```kql
Users
| extend display_name = coalesce(nickname, name, "unknown")
| project display_name
```

## Pattern: null and emptiness checks

```kql
Users
| where isnotnull(email) and isnotempty(email)
```

These helpers are especially useful when you are cleaning semi-structured or user-entered data.

## String transformation patterns

## Pattern: build a composite key

```kql
Events
| extend key = strcat(user, ":", city)
| project key, value
```

## Pattern: trim and normalize text

```kql
Users
| extend normalized = tolower(trim(name))
| project normalized
```

## Pattern: slice strings with 0-based indexing

```kql
Users
| extend prefix = substring(name, 0, 3)
| project name, prefix
```

AdxLite uses 0-based substring indexing, matching the implementation in the translator and pandas fallback layer.

## `.append` command usage

The `.append` command materializes a query result into an existing table.

### Basic pattern

```kql
.append Archive <| Events | where ok == true
```

### Typical workflow

1. create an empty destination table with the desired schema
2. run a query that returns matching columns in matching order
3. append those rows into the destination table

### Example

```python
archive = pd.DataFrame(
    {
        "user": pd.Series(dtype="string"),
        "city": pd.Series(dtype="string"),
        "value": pd.Series(dtype="int64"),
        "ok": pd.Series(dtype="bool"),
        "ts": pd.Series(dtype="datetime64[ns]"),
    }
)

with AdxLiteClient(":memory:") as client:
    client.ingest("Events", events)
    client.ingest("Archive", archive)
    client.query('.append Archive <| Events | where ok == true')
    print(client.query('Archive | count'))
```

### Notes

- `.append` returns an empty DataFrame
- append validation still applies, so the query output schema must match the destination schema exactly
- `.append` is local-only; it does not move data to or from external systems

## Recommended query-writing habits

- filter early when possible
- keep parse late in the pipeline unless its output is required sooner
- use explicit conversion for JSON scalars
- prefer readable multi-line pipelines over overly compressed single-line queries
- inspect intermediate projections during debugging

## Putting it all together

A realistic AdxLite query may combine several advanced patterns:

```kql
Logs
| where Message matches regex "login|logout"
| parse Message with "user=" user " action=" action " payload=" payload
| extend count = toint(extractjson("$.count", payload))
| extend bucket = bin(ts, 1h)
| summarize total=count(), max_count=max(count) by bucket, action
| sort by bucket asc, action asc
```

This example shows the intended style of the engine:

- SQLite handles the early filter and aggregate-friendly operations
- pandas handles `parse`
- JSON helpers and conversions make semi-structured payloads usable
- the final result is a normal pandas DataFrame

## Pattern: scalar let for reusable thresholds

Use `let` to define a scalar constant and reference it across the pipeline.

```kql
let threshold = 100;
Events
| where value > threshold
| summarize cnt = count() by city
```

## Pattern: tabular let for intermediate results

Define a named sub-query with `let` and reference it as a table later.

```kql
let HighValue = Events | where value > 100;
HighValue
| summarize total = sum(value) by city
```

## Pattern: combine tables with union

Use source-form union to query across multiple tables:

```kql
union Events, Logs
| where ts > ago(1d)
| summarize cnt = count() by source_table = $table
```

Use `withsource` to add a column that identifies which table each row came from:

```kql
union withsource=origin Events, Logs
| summarize cnt = count() by origin
```

Pipe-form union appends another table inside a pipeline:

```kql
Events
| union Logs
| where city == "London"
```

## Pattern: correlate tables with join

Inner join matches rows from two tables on a key:

```kql
Events
| join kind=inner (Users) on user
| project user, city, email
```

Left outer join keeps all rows from the left, filling NaN for unmatched right columns:

```kql
Events
| join kind=leftouter (Users) on user
| project user, city, email
```

Left anti join finds rows in the left table with no match in the right:

```kql
Events
| join kind=leftanti (Users) on user
| project user, city
```

### Qualified key columns

When the join keys have different names in each table, use `$left` and `$right`:

```kql
Events
| join kind=inner (Users) on $left.user_id == $right.id
| project user_id, city, email
```

### Join with sub-pipeline

The right side of a join can be a full pipeline:

```kql
Events
| join kind=inner (Users | where active == true) on user
| project user, city
```

## Pattern: combine let with join

Use `let` to define the right-side table, then join against it:

```kql
let ActiveUsers = Users | where active == true;
Events
| join kind=inner (ActiveUsers) on user
| project user, city, email
```

## Related documents

- [Quickstart](quickstart.md)
- [Ingestion guide](ingestion.md)
- [Functions reference](../reference/functions.md)
- [Operators reference](../reference/operators.md)
- [Limitations](../reference/limitations.md)
