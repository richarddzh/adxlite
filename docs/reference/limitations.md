# Limitations

This document describes the boundaries of AdxLite's current implementation. The goal is to make limitations explicit so that users can decide when AdxLite is the right tool and when a fuller Kusto environment or a different local engine would be more appropriate.

For supported syntax, see [KQL syntax](kql-syntax.md). For design rationale, see [Design decisions](../design/decisions.md).

## Philosophy of limitations

AdxLite is intentionally narrow. It aims to be a reliable, well-tested local analytics tool for Python developers, not a full Azure Data Explorer replacement. Many limitations are therefore deliberate scope choices rather than accidental gaps.

## Unsupported KQL tabular operators

The parser explicitly treats several KQL operators as unsupported.

| Operator | Status | Why unsupported right now | Typical workaround |
| --- | --- | --- | --- |
| `join` | **supported** | All 9 join kinds are supported | — |
| `union` | **supported** | Source and pipe forms, kind=inner/outer, withsource | — |
| `let` | **partially supported** | Scalar and tabular let; function let unsupported | Build queries in Python strings for function-like reuse |
| `mv-expand` | unsupported | Needs array/dynamic expansion semantics not present in the current dynamic model | deserialize JSON in Python and re-ingest flattened rows |
| `mv-apply` | unsupported | Depends on dynamic expansion plus subquery semantics | perform the logic in pandas before ingestion |
| `render` | unsupported | Visualization is outside the scope of a local query engine | use pandas plotting or notebook/charting tools after query execution |
| `invoke` | unsupported | Depends on stored-function or function-object semantics not present in the engine | call Python helpers around queries instead |
| `evaluate` | unsupported | Opens a broad plugin/operator surface outside the current execution model | perform custom post-processing in Python |

## Unsupported or missing expression/operator forms

Even within supported categories, some KQL spellings are intentionally absent.

| Form | Current state | Workaround |
| --- | --- | --- |
| `!contains` | not parsed as a dedicated token | use `not (col contains "x")` |
| `!has` | not parsed as a dedicated token | use `not (col has "x")` |
| `!in` | not parsed as a dedicated token | use `not in (...)` |
| `!between` | not parsed as a dedicated token | use `not between (...)` |
| function `let` (lambdas) | unsupported | define logic in Python and compose query strings |
| wildcard union (`union T*`) | unsupported | list table names explicitly |
| `innerunique` true dedup | approximated as `inner` in SQL path | pandas fallback provides true dedup |

## Unsupported KQL function surface

AdxLite implements a useful set of functions, but it does **not** implement the full Kusto function library.

Examples of unsupported categories include:

- advanced array functions
- bag/object manipulation beyond JSON text extraction
- geo functions
- window functions such as `row_number()` in true Kusto style
- many statistical, series, and machine-learning helpers
- cluster or database metadata functions

If a query calls an unsupported scalar function, AdxLite raises `KqlUnsupportedError` during translation or pandas execution.

## Behavioral differences from real Kusto

Even when a name is supported, behavior may differ from Azure Data Explorer.

## Difference: local-only execution

AdxLite never connects to an external Kusto cluster.

Implication:

- all data must be ingested locally
- there is no concept of querying remote tables, databases, or clusters

## Difference: dynamic values are JSON text

AdxLite's `dynamic()` and `parse_json()` behave as JSON-text normalization helpers, not as a full nested dynamic runtime type.

Implication:

- JSON values usually appear as strings in query results
- `extractjson()` often returns string values for scalars
- if you need a numeric result, convert it explicitly with `toint()` or `todouble()`

## Difference: `parse` runs in pandas

The `parse` operator is implemented through the hybrid SQL-plus-pandas execution path.

Implication:

- rows must leave SQLite and enter pandas once the pipeline hits `parse`
- very large intermediate row sets can be more expensive than pure SQL queries
- `parse` captures always become string columns

## Difference: regex matching is partial

`matches regex` uses partial-match semantics, equivalent to a regex search, not a full-string match.

Implication:

- patterns match anywhere in the text unless you anchor them yourself with `^` and `$`

## Difference: `startswith` and `endswith` rely on SQLite `LIKE`

In the SQL path, these operators are translated through SQLite `LIKE`.

Implication:

- exact case sensitivity may differ from Kusto expectations depending on SQLite collation behavior
- when you need predictable case behavior, normalize explicitly with `tolower()` or `toupper()`

## Difference: datetime storage model

Datetimes are stored as ISO-8601 strings with metadata rather than a native database datetime type.

Implication:

- datetime behavior is reliable for the supported helpers and normalized values
- it is not identical to the full Kusto datetime type system

## Difference: simplified `datetime_add()` signature

AdxLite supports `datetime_add(timespan, value)`.

Implication:

- if you are used to a different Kusto variant that splits unit and amount, adapt queries to the simpler two-argument form

## Difference: integer schema inference uses `long`

DataFrame integer columns infer to `long` rather than a distinct stored `int` type.

## Performance considerations

AdxLite is fast enough for many local workloads, but it is still a lightweight embedded engine.

## SQL path is usually fastest

Queries composed of SQL-compatible operators such as `where`, `project`, `extend`, `summarize`, `sort by`, and `top` benefit most from SQLite execution.

Recommendation:

- push filters early
- aggregate before materializing unnecessary rows
- keep pipelines SQL-only when possible for larger datasets

## Hybrid queries cost more

Any pipeline that reaches `parse` transitions into pandas execution for the remaining suffix.

Recommendation:

- filter as much as possible before `parse`
- avoid bringing huge text-heavy row sets into the pandas suffix unnecessarily

## Ingestion is row-materializing

AdxLite writes normalized DataFrame rows into SQLite. This is fine for local datasets, but not a substitute for a high-throughput ingestion service.

Recommendation:

- batch ingestion when loading incrementally
- reuse file-backed databases instead of rebuilding from scratch if your workflow is iterative

## SQLite limitations that affect behavior

Some limitations are inherited directly from SQLite.

### Type affinity is limited

SQLite does not have a rich static type system like a warehouse engine.

Effect on AdxLite:

- logical schema metadata is required to preserve intent
- some expression results rely on runtime restoration rather than native database typing

### No built-in regex operator with KQL semantics

Effect on AdxLite:

- regex support is implemented through Python-backed UDFs
- performance depends on row volume and UDF invocation overhead

### Limited built-in datetime semantics

Effect on AdxLite:

- AdxLite implements datetime helpers itself through UDFs
- supported behavior is good for the documented subset, but not equivalent to the full Kusto datetime engine

### No native JSON dynamic runtime equivalent to Kusto

Effect on AdxLite:

- JSON is handled as text with helper functions rather than as a full dynamic object model

## Workarounds and best practices

| Need | Suggested workaround |
| --- | --- |
| Join two datasets | merge in pandas first, then ingest the result |
| Union compatible datasets | append them into one table before querying |
| Expand JSON arrays | transform in pandas and re-ingest flattened rows |
| Predictable case-insensitive prefix/suffix tests | use `tolower(col)` with lowercase literals |
| Numeric JSON values | wrap `extractjson()` with `toint()` or `todouble()` |
| Reusable intermediate results | materialize them into a table with `.append` |
| Remote analytics | use a real Azure Data Explorer environment instead of AdxLite |

## When AdxLite is a good fit

AdxLite works well when you need:

- local and reproducible analytics
- embedded query capability in Python apps or tests
- a practical KQL subset rather than full Kusto parity
- a small dependency footprint
- pandas-friendly inputs and outputs

## When to choose something else

Consider a different tool when you need:

- full Azure Data Explorer compatibility
- distributed or remote query execution
- multi-table relational analytics with joins and unions
- large-scale columnar analytics beyond the scope of local SQLite
- complex dynamic/array transformations inside the query language

## Related documents

- [Design decisions](../design/decisions.md)
- [Architecture](../design/architecture.md)
- [Operators reference](operators.md)
- [Functions reference](functions.md)

## let/union/join specific limitations

### let

- **Function let is not supported.** Only scalar literals/expressions and tabular pipelines.
- Scalar let values must be literals or simple arithmetic (no function calls in let expressions).
- Tabular let creates a temporary table; very large tabular lets consume memory and SQLite temp storage.
- Column names always take precedence over let variable names (Kusto semantics).

### union

- **Wildcard table names not supported** (`union T*` will fail).
- **Sub-pipeline arguments not supported** (`union (T1 | where x > 5), T2`).
- `isfuzzy` parameter is not supported.
- Union of tables with mismatched schemas falls through to pandas execution (slower for large datasets).

### join

- **`innerunique` is treated as `inner` in SQL mode** — right-side deduplication only applies in pandas fallback.
- `fullouter` and `rightouter` always execute in pandas (SQLite has no native support).
- `hint.strategy` parameters are ignored.
- Cross-database joins are not supported (all tables must be in the same local database).
- The `_right` suffix for conflicting column names may differ from Kusto's exact behavior in some edge cases.
