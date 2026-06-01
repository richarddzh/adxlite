# Design Decisions

This document explains the major design choices behind AdxLite. The goal is not just to list decisions, but to show the alternatives that were considered and the tradeoffs that shaped the current implementation. For structural details, see [Architecture](architecture.md). For user-visible behavior, see [Limitations](../reference/limitations.md) and [Type system](type-system.md).

## Decision summary

| Topic | Chosen approach |
| --- | --- |
| Storage engine | SQLite |
| Data interchange | pandas DataFrames |
| Query language | Supported subset of KQL |
| Execution model | Hybrid SQL first, pandas fallback |
| Query composition | Nested subqueries for each pipeline stage |
| Scalar extensions | SQLite UDFs plus pandas row-wise equivalents |
| Datetime storage | ISO-8601 text with metadata |
| SQL safety | Parameterized queries |

## Why SQLite

SQLite is the core persistence engine for AdxLite.

### Reasons for choosing SQLite

- it is embedded and requires no separate service process
- it is available in the Python standard library through `sqlite3`
- it supports SQL execution, aggregation, sorting, filtering, and user-defined functions
- it stores data in a single file, which is ideal for local workflows and tests
- it is mature, stable, and widely understood by Python developers

### Why not DuckDB

DuckDB is also an excellent embedded analytics engine, but AdxLite did not choose it for this implementation.

Tradeoffs that favored SQLite here:

- SQLite is in the Python standard library; DuckDB adds another runtime dependency
- SQLite UDF registration is simple and sufficient for the supported function set
- AdxLite does not currently target high-end analytical SQL features where DuckDB would provide the biggest advantage
- the project goal emphasizes lightweight local embedding over maximum analytical throughput

This does **not** mean DuckDB is a poor fit in general. It means SQLite is a better fit for AdxLite's current requirements: a minimal-dependency local KQL engine with predictable packaging.

### Why not pure pandas storage

Pandas is great for in-memory transformation, but poor as the only persistence layer for this project.

Reasons not to use pure pandas as the storage engine:

- there is no built-in durable table store equivalent to a SQLite database file
- query pushdown becomes harder because everything is already in memory
- grouped aggregations, filters, and projections would require a full custom execution engine for all queries
- reproducible local file-backed state is a first-class requirement

The chosen model uses pandas where it is strong—ingestion, result handling, and certain post-processing—but delegates durable storage and most query execution to SQLite.

## Why hybrid execution instead of pure SQL

AdxLite uses SQL as the primary execution target, but not the only one.

### Reason for the hybrid model

Some KQL features map naturally to SQL, while others are awkward or brittle in SQLite-only form. The `parse` operator is a good example: it is easier to implement accurately in pandas using regex extraction over strings than to force it into complex SQL expressions.

Benefits of the hybrid approach:

- most queries remain efficient because filtering and aggregation stay in SQLite
- advanced operators can still be supported without blocking on SQL expressiveness
- the system can add new pandas-only operators later without redesigning the public API

### Why not pure SQL

A pure-SQL design would simplify the runtime story, but it would also narrow the supported KQL subset further or require increasingly complex SQL generation.

Costs of pure SQL:

- some operators would become impractical to implement cleanly
- regex-based extraction logic would be harder to express and maintain
- function semantics would depend even more heavily on SQLite quirks
- adding support for advanced KQL surface area would be slower

### Why not pure pandas

A pure-pandas engine would make every operator possible in Python, but it would sacrifice the benefits of SQLite.

Costs of pure pandas:

- no built-in persistent local database file
- higher memory cost because the whole working set lives in Python objects
- more custom code for operations already solved by SQL
- more work to guarantee deterministic pipeline semantics and append behavior

The hybrid approach is a deliberate middle path: SQL for the common path, pandas for the hard edges.

## Why nested subqueries for pipeline correctness

The SQL translator wraps every pipeline stage in a nested subquery.

Example conceptually:

```text
SELECT * FROM (
  SELECT * FROM (
    SELECT * FROM "Users"
  ) AS _t
  WHERE "score" >= ?
) AS _t
ORDER BY "score" DESC
```

### Reason for this choice

KQL pipelines are ordered transformations. Each operator acts on the output of the previous operator, not on the original source table. Nested subqueries mirror that model directly.

Benefits:

- easy-to-follow one-stage-at-a-time translation
- prevents accidental reordering of semantics between `project`, `extend`, `where`, and `summarize`
- makes debugging generated SQL easier because every KQL operator corresponds to a visible SQL boundary
- simplifies future extension because each operator can assume it receives a table-like input named `_t`

### Why not flatten the SQL aggressively

A more sophisticated translator could attempt to collapse multiple stages into a flatter SQL statement. That would reduce nesting, but it adds complexity and optimization concerns.

Costs of flattening:

- more intricate alias management
- harder reasoning about expressions introduced by `extend` or `project`
- higher risk of semantic bugs when operator order matters
- less obvious correspondence between KQL text and generated SQL

Given AdxLite's goals, the explicit nested approach is the safer choice.

## Why SQLite UDFs for math, regex, datetime, and JSON helpers

AdxLite implements many scalar helpers as SQLite UDFs and mirrors them in pandas for fallback execution.

### Reasons for UDFs

- SQLite lacks many KQL-style helpers out of the box
- UDFs keep scalar evaluation inside the SQL path for SQL-compatible queries
- the translator can emit stable function names such as `kql_bin()` or `kql_regex_match()`
- the same logical helper can be reused from pandas fallback code

Examples of UDF-backed behavior:

- regex partial matching via `kql_regex_match`
- capture extraction via `kql_regex_extract`
- datetime bucketing via `kql_bin`
- timespan-aware datetime math via `kql_ago` and `kql_datetime_add`
- JSON extraction via `kql_extractjson`

### Why not make pandas the first stop for these features

A pandas-first design would work, but it would pull more queries out of SQLite than necessary.

Costs of pandas-first evaluation:

- more rows transferred from SQLite into Python
- less benefit from database-side filtering and aggregation
- more duplicated logic between SQL-compatible and pandas-only paths

UDFs let AdxLite keep many expressions in the SQL path while still supporting KQL-inspired semantics.

## Why ISO-8601 text for datetime storage

AdxLite stores datetimes as ISO-8601 strings in SQLite `TEXT` columns and tracks logical type information in metadata.

### Reasons for this choice

- ISO-8601 is readable and portable
- lexical ordering aligns well with chronological ordering for normalized timestamps
- SQLite has no dedicated datetime storage type, so text is a practical representation
- the values round-trip cleanly through pandas `to_datetime`
- UDFs can parse and emit the same representation consistently

### Alternatives considered

#### Unix epoch integers or floats

Pros:

- efficient numeric comparisons
- compact representation

Cons:

- less readable in raw SQLite inspection
- needs a representation choice for seconds vs milliseconds vs microseconds
- more conversion overhead for formatting and display
- makes manual inspection and debugging harder

#### Raw SQLite date/time functions without metadata

Pros:

- simple initial implementation

Cons:

- loses explicit logical type tracking
- makes result restoration ambiguous
- complicates append validation and schema inspection

The chosen combination of ISO text plus metadata balances simplicity, readability, and recoverable type information.

## Why parameterized queries

The SQL translator binds literal values as parameters instead of interpolating them directly into SQL strings.

### Reasons for parameterization

- protects against SQL injection when query literals contain quotes or special characters
- avoids manual escaping rules in most expression translation paths
- produces more predictable SQL generation logic
- clearly separates the query template from user-provided values

### Why this matters even for a local database

Local-only does not mean untrusted input is impossible. A desktop app, notebook, CLI, or test harness may still build KQL from user-supplied text. Parameterization is a correctness and safety choice, not just a networked-service requirement.

## Why schema metadata exists separately from SQLite types

The metadata table stores logical KQL types and original column order.

Reasons:

- SQLite affinity is not rich enough to express the full logical intent needed by AdxLite
- datetime columns are stored as text but must be restored as pandas datetime dtype
- append validation must compare logical schemas, not just raw SQL column definitions
- public schema inspection should return KQL-style types such as `long` and `datetime`

Without metadata, important behaviors would become guesswork at query time.

## Why `project-away` is resolved during planning

`project-away` is not translated directly to SQL. Instead, the planner rewrites it to a positive `project` based on the known current schema.

Reasons:

- SQL needs an explicit select list to drop named columns safely
- the planner already tracks schema after each operator
- rewriting once simplifies both SQL translation and pandas execution
- it keeps the translator focused on positive relational projections

This is an example of the planner doing semantic normalization before execution.

## Why `.append` is a query command instead of a separate Python-only feature

AdxLite supports `.append TableName <| query` as part of the query language because it matches KQL users' expectations for a lightweight management-style command and reuses the same execution machinery as normal query pipelines.

Benefits:

- allows query-driven local materialization
- keeps append semantics visible in KQL scripts and tests
- avoids introducing a second, unrelated command model for query-to-table workflows

## Tradeoffs accepted by the current design

No design decision is free. AdxLite intentionally accepts the following tradeoffs:

- SQLite is simpler than a full analytical engine, but also less feature-rich
- hybrid execution is flexible, but introduces a split between SQL and pandas semantics
- nested subqueries are easy to reason about, but not always the most compact SQL shape
- ISO datetime text is readable, but not as compact as epoch storage
- a KQL subset is easier to document and test, but narrower than full Kusto

## Alternatives not chosen right now

| Alternative | Why it was not chosen |
| --- | --- |
| Full Azure Data Explorer compatibility | Too large in scope for a lightweight local library |
| Remote cluster connectivity | Violates the local-first requirement |
| Cross-database joins/unions | Complicates the model beyond current goals |
| A cost-based optimizer | Unnecessary for the current supported feature set |
| SQL string interpolation | Less safe and less maintainable than parameters |
| Datetime-only pandas execution | Would pull too much work out of SQLite |

## How these decisions affect users

Users see the consequences of these decisions in practical ways:

- setup is easy because there is no external service
- queries return DataFrames naturally because pandas is a first-class integration point
- some advanced KQL features are unavailable because the project favors a well-tested subset
- datetime and regex helpers work locally because UDFs bridge SQLite feature gaps
- query performance is usually good for local analytic workloads because the SQL path handles the bulk of the work

## Related documents

- [Architecture](architecture.md) shows where each decision appears in the code layout.
- [Type system](type-system.md) explains the consequences of the datetime and schema choices.
- [Limitations](../reference/limitations.md) describes the boundaries created by these decisions.
