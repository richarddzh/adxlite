# Functional Requirements

This document captures the complete functional requirement set for AdxLite as implemented and documented in this repository. It is intended to be read by maintainers, contributors, and reviewers who want a single place that explains the required behavior of the project.

The requirements below are written as product-level capabilities rather than low-level implementation tasks. Where useful, each requirement includes rationale, expected behavior, and validation notes.

## Scope statement

AdxLite is a local, SQLite-based analytical engine that accepts a supported subset of KQL and operates over tables ingested from pandas DataFrames. The product must remain local-first, easy to embed in Python programs, and sufficiently documented for users to understand both supported behavior and limitations without reading the source.

## Requirement summary table

| ID | Requirement | Status expectation |
| --- | --- | --- |
| FR-01 | SQLite-based local file database | mandatory |
| FR-02 | Pandas DataFrame ingestion as tables | mandatory |
| FR-03 | KQL query support over local tables | mandatory |
| FR-04 | `.append` command support | mandatory |
| FR-05 | Simple client API | mandatory |
| FR-06 | No external Kusto cluster connections | mandatory |
| FR-07 | No join/union across databases | mandatory |
| FR-08 | `parse` operator support | mandatory |
| FR-09 | `ago()` and `now()` support | mandatory |
| FR-10 | `matches regex` partial-match semantics | mandatory |
| FR-11 | `extract()` function support | mandatory |
| FR-12 | `log()`, `log10()`, `pow()`, `sqrt()` support | mandatory |
| FR-13 | `parse_json()` and `dynamic()` support | mandatory |
| FR-14 | DateTime type support | mandatory |
| FR-15 | Empty-table aggregation behavior | mandatory |
| FR-16 | Rich documentation | mandatory |
| FR-17 | Proper module architecture | mandatory |
| FR-18 | Comprehensive tests | mandatory |

## FR-01: SQLite-based local file database

AdxLite must use SQLite as its storage engine.

Expected behavior:

- tables are stored in a SQLite database file or in-memory database
- no external service is required to create, query, or mutate data
- the database connection is created through Python's SQLite support

Validation ideas:

- instantiate `AdxLiteClient("analytics.db")`
- ingest data
- reopen the file and confirm tables persist

## FR-02: Pandas DataFrame ingestion as tables

AdxLite must ingest pandas DataFrames into queryable tables.

Expected behavior:

- `ingest_from_pandas()` must exist as a public API
- `ingest()` may exist as the primary implementation or alias
- the table name must become queryable immediately after ingestion
- schema metadata must be recorded for later restoration and validation

Validation ideas:

- ingest a DataFrame with string, numeric, bool, and datetime columns
- confirm `list_tables()` shows the new table
- confirm `get_schema()` reports inferred logical types

## FR-03: KQL query support (virtual Kusto database)

AdxLite must support querying local tables with a documented subset of KQL.

Expected behavior:

- the query language must be KQL-inspired pipeline syntax
- supported operators and functions must be documented
- results must be returned as pandas DataFrames
- queries must run entirely against local ingested tables

Validation ideas:

- run representative `where`, `project`, `extend`, `summarize`, and `sort by` queries
- confirm output matches expected DataFrame content

## FR-04: `.append` command

AdxLite must support a KQL-style append command that writes query results into a local table.

Expected behavior:

- syntax must follow `.append TableName <| query`
- the nested query must run through the normal planning and execution path
- the command must append rows using existing schema validation
- the command should return an empty pandas DataFrame after success

Validation ideas:

- create a destination table
- append filtered rows from another table
- query the destination table and confirm new rows were written

## FR-05: Simple client API

AdxLite must provide a small, easy-to-understand Python API.

Expected behavior:

- a public `AdxLiteClient` class must exist
- the client must expose ingestion, query, schema inspection, table listing, dropping, and closing operations
- the client must support context manager usage

Validation ideas:

- instantiate the client
- call every public method at least once in tests or examples
- confirm the context manager closes cleanly

## FR-06: No external Kusto cluster connections

AdxLite must remain local-only and must not require or attempt remote Azure Data Explorer connectivity.

Expected behavior:

- no connection strings, cluster URIs, or remote auth flows are required
- all data must originate from local ingestion
- documentation must make the local-only model explicit

Validation ideas:

- inspect the public API and configuration surface
- confirm no cluster connection API exists

## FR-07: No join/union across databases

AdxLite must not support multi-database relational composition such as cross-database joins or unions.

Expected behavior:

- unsupported operators such as `join` and `union` should raise `KqlUnsupportedError`
- documentation must state that the supported model is a single local database with single-table pipelines

Validation ideas:

- parse or query a statement containing `join` or `union`
- confirm an unsupported-error path is triggered

## FR-08: `parse` operator support

AdxLite must support the KQL `parse` operator.

Expected behavior:

- the parser must recognize `parse <expr> with <pattern>`
- capture variables must be added as new columns
- wildcard `*` segments must skip text without capturing
- execution may use pandas post-processing if SQL-only execution is unsuitable

Validation ideas:

- ingest a log message column
- parse user and action fields from the message text
- confirm projected capture columns match expected values

## FR-09: `ago()` and `now()` functions

AdxLite must support current-time and relative-time datetime helpers.

Expected behavior:

- `now()` must return a current UTC timestamp representation
- `ago(timespan)` must subtract a supported timespan from the current UTC timestamp
- both functions must be usable in query expressions

Validation ideas:

- run queries using `now()` and `ago(1d)` in filters or `extend`
- confirm outputs are valid datetime-like strings or restored values as documented

## FR-10: `matches regex` with partial-match semantics

AdxLite must support the `matches regex` operator using partial-match behavior.

Expected behavior:

- the operator must return true when the pattern matches any substring, not just the whole string
- regex matching must be available both in SQLite execution and pandas fallback execution
- documentation must clearly state the partial-match semantics

Validation ideas:

- evaluate a query such as `Message matches regex "err.."`
- confirm a row with `prefix error suffix` is matched

## FR-11: `extract()` function

AdxLite must support regex capture extraction through `extract()`.

Expected behavior:

- the function must accept a pattern, group index, and text value
- it must return the captured subgroup or null when no match is found
- documentation must explain the return type and group numbering expectations

Validation ideas:

- query `extract("user=(\w+)", 1, Message)` on sample rows
- confirm the returned value is the captured user name

## FR-12: Math function support

AdxLite must support at least `log()`, `log10()`, `pow()`, and `sqrt()`.

Expected behavior:

- the functions must be callable in expressions such as `extend`
- results must use numeric return values
- the SQL and pandas execution layers must behave consistently enough for documented examples and tests

Validation ideas:

- ingest numeric columns
- compute logarithms, powers, and roots in a query
- compare results with Python expectations

## FR-13: `parse_json()` and `dynamic()` support

AdxLite must support JSON parsing helpers.

Expected behavior:

- `parse_json(x)` and `dynamic(x)` must exist
- JSON values may be represented as JSON text rather than full nested object types in results
- `extractjson()` must allow pulling values from JSON text

Validation ideas:

- ingest JSON text payloads
- parse and extract fields in a query
- confirm documented result behavior

## FR-14: DateTime type support

AdxLite must support datetime ingestion, storage, comparison, and helper functions.

Expected behavior:

- pandas datetime columns must be detected during ingestion
- storage must preserve enough information for correct ordering and restoration
- result columns typed as datetime must be restored to pandas datetime dtype where applicable
- datetime helpers such as `bin`, `datetime_diff`, `format_datetime`, and `datetime_add` must be supported as documented

Validation ideas:

- ingest datetime columns
- query with datetime filters and computed buckets
- confirm round-trip dtype restoration

## FR-15: Empty table aggregation

AdxLite must support sensible aggregation behavior on empty tables.

Expected behavior:

- `count()` on an empty input must return `0`
- aggregate queries against empty tables must still return a row when appropriate for the summarize form being used
- null-like results for aggregates such as `sum` and `avg` should be documented clearly

Validation ideas:

- ingest an empty DataFrame with a numeric column
- run `summarize total=count(), sum_value=sum(value)`
- confirm `total == 0`

## FR-16: Rich documentation

AdxLite must include documentation that is detailed enough for a user to understand the product without reading the source code.

Expected behavior:

- architecture, decisions, type system, requirements, guides, reference docs, and project README must exist
- each document should include explanation, examples, parameter notes, return value notes, and cross-references where relevant
- limitations and behavioral differences from Azure Data Explorer must be explicit

Validation ideas:

- review the documentation set for completeness and internal consistency
- confirm that major APIs, operators, functions, and constraints are documented

## FR-17: Proper module architecture

AdxLite must keep a clear separation between API, parsing, translation, storage, and execution concerns.

Expected behavior:

- the repository should contain distinct modules for the public client, parser, translator, storage, and engine layers
- responsibilities should remain understandable and reviewable
- the architecture should support future extension without collapsing all logic into a single file

Validation ideas:

- inspect the module tree
- confirm responsibilities match the documentation in [Architecture](architecture.md)

## FR-18: Comprehensive tests

AdxLite must include automated tests covering the supported feature set.

Expected behavior:

- parser tests must exist
- translator tests must exist
- unit tests for UDF behavior must exist
- integration tests must cover query execution, datetime handling, advanced functions, and append behavior

Validation ideas:

- run `python -m pytest -q`
- confirm the suite passes
- review test files for coverage of representative features

## Non-requirement clarifications

The following are intentionally **not** required by the current scope:

- external Kusto cluster connectivity
- full Azure Data Explorer feature parity
- distributed execution
- cross-database joins or unions
- remote metadata catalogs
- automatic dynamic-object expansion to nested Python structures in result DataFrames

## Traceability to documentation

Each major requirement is covered elsewhere in the docs.

| Requirement area | Primary reference |
| --- | --- |
| Client API | [API reference](../reference/api.md) |
| Query operators | [Operators reference](../reference/operators.md) |
| Functions | [Functions reference](../reference/functions.md) |
| Architecture | [Architecture](architecture.md) |
| Storage and types | [Type system](type-system.md) |
| Usage examples | [Quickstart](../guides/quickstart.md), [Advanced queries](../guides/advanced-queries.md) |
| Limitations | [Limitations](../reference/limitations.md) |

## Review checklist

When evaluating changes to AdxLite, use this checklist:

- does the change preserve local-only execution?
- does it keep the client API simple?
- is the supported behavior covered by tests?
- is the behavior documented in the relevant guide or reference page?
- does it preserve or intentionally extend the supported KQL subset?

## Related documents

- [Architecture](architecture.md)
- [Design decisions](decisions.md)
- [API reference](../reference/api.md)
- [Limitations](../reference/limitations.md)
