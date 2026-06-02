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
| FR-19 | `let` statement support | mandatory |
| FR-20 | `union` operator support | mandatory |
| FR-21 | `join` operator support | mandatory |
| FR-22 | Wrap single-DataFrame quick-query API (adxpandas) | mandatory |
| FR-23 | Jupyter magic commands (adxpandas) | mandatory |
| FR-24 | `render` operator chart visualization (adxpandas) | mandatory |

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

- cross-database references (e.g., `database("other").Table`) should raise an error
- all tables in `join` and `union` must exist in the same local database
- documentation must state that the supported model is a single local database

Validation ideas:

- join or union a table that does not exist in the local database
- confirm a `TableNotFoundError` is raised

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

## FR-19: `let` statement support

AdxLite must support `let` bindings for naming scalar values and tabular sub-queries.

### Supported forms

| Form | Example | Supported |
|------|---------|-----------|
| Scalar let | `let threshold = 100; T \| where val > threshold` | Yes |
| Tabular let | `let errors = T \| where level == "error"; errors \| count` | Yes |
| Function let | `let f = (x: int) { x * 2 };` | No (raise KqlUnsupportedError) |

### Expected behavior

- Multiple `let` bindings separated by `;` before the main query body
- Scalar lets substitute as literal values in subsequent expressions
- Tabular lets execute the sub-pipeline and make the result available as a table name
- Column names in the current row scope take precedence over scalar let names (matching Kusto semantics)
- Tabular let results are cleaned up after the main query completes
- Later let bindings can reference earlier let bindings

### Validation ideas

- `let x = 5; T | where col > x` returns correct filtered result
- `let filtered = T | where active == true; filtered | count` returns correct count
- Column named same as let variable: column wins
- Undefined let reference: error

## FR-20: `union` operator support

AdxLite must support combining rows from multiple local tables using `union`.

### Supported forms

| Form | Example | Supported |
|------|---------|-----------|
| Source form | `union T1, T2 \| where x > 5` | Yes |
| Pipe form | `T1 \| union T2, T3` | Yes |
| kind=outer (default) | All columns from all tables, NULL for missing | Yes |
| kind=inner | Only columns common to all tables | Yes |
| withsource=col | Adds a column indicating source table name | Yes |
| Sub-pipeline args | `union (T1 \| where x > 5), T2` | No (MVP) |

### Expected behavior

- Schema alignment: columns missing in a table are filled with NULL (kind=outer)
- Column ordering: first table's columns come first, then new columns from subsequent tables
- `kind=inner`: only columns present in ALL tables appear in the result
- `withsource=colname`: prepends a string column with the source table name per row
- Works both as a source (before pipe) and as a pipe operator
- Union of empty tables produces an empty result with correct schema

### Validation ideas

- Union two tables with same schema: row count = sum
- Union tables with different schemas: NULL fill verified
- kind=inner: verify only common columns in output
- withsource: verify source column content
- Union followed by where/summarize

## FR-21: `join` operator support

AdxLite must support joining two local tables based on key columns.

### Supported join kinds

| Kind | Behavior | Output columns |
|------|----------|----------------|
| `innerunique` (default) | Rows matching on both sides | Left + right |
| `inner` | All matching row combinations | Left + right |
| `leftouter` | All left rows, matched right or NULL | Left + right |
| `rightouter` | All right rows, matched left or NULL | Left + right |
| `fullouter` | All rows from both, NULL where unmatched | Left + right |
| `leftanti` | Left rows with NO match on right | Left only |
| `leftsemi` | Left rows with at least one match on right | Left only |
| `rightanti` | Right rows with NO match on left | Right only |
| `rightsemi` | Right rows with at least one match on left | Right only |

### Supported syntax forms

| Form | Example |
|------|---------|
| Simple key | `T1 \| join T2 on key` |
| With kind | `T1 \| join kind=leftouter T2 on key` |
| Multi-key | `T1 \| join T2 on key1, key2` |
| Qualified keys | `T1 \| join T2 on $left.id == $right.user_id` |
| Right sub-pipeline | `T1 \| join kind=inner (T2 \| where x > 5) on id` |

### Output column naming rules

- Join key columns (simple form): appear once in output (from left side)
- Left non-key columns: keep original names
- Right non-key columns: if name conflicts with left column, suffix with `_right`
- Anti/semi joins: only output the relevant side's columns

### Expected behavior

- Default join kind is `innerunique` (treated as `inner` for MVP — no automatic right-side dedup)
- Right side can be a full sub-pipeline enclosed in parentheses
- NULL keys do not match (SQL semantics)
- All tables must be in the same local database (no cross-database joins)

### Validation ideas

- Inner join: verify only matching rows appear
- Left outer: verify NULL fill for unmatched right
- Left anti: verify only non-matching left rows
- Left semi: verify matching left rows without duplication
- Multi-key join: verify correct matching
- Column conflict: verify `_right` suffix
- Join with empty right table: left outer returns all left rows with NULL
- Right side sub-pipeline: verify filter applies before join

## FR-22: Wrap single-DataFrame quick-query API (adxpandas)

adxpandas must provide a `Wrap` class that wraps a single DataFrame for quick KQL queries with method chaining.

### Rationale

Many users work with a single DataFrame and want a quick, fluent way to apply KQL operators without setting up a client and registering tables. The Wrap pattern (inspired by KustoPandas) provides this.

### Expected behavior

- `Wrap(df)` wraps any pandas DataFrame
- `w.execute("self | where x > 1 | project name")` runs a query using `self` as the table name
- `execute()` returns a new `Wrap` for further chaining (or `RenderResult` if query ends with render)
- Convenience methods `.where()`, `.project()`, `.extend()`, `.summarize()`, `.sort()`, `.take()`, `.top()`, `.count()`, `.distinct()`, `.project_away()` each return a new `Wrap`
- `.render()` returns a `RenderResult` (not chainable — terminal operation)
- `.df` property exposes the underlying DataFrame
- `_repr_html_()` delegates to DataFrame for Jupyter display
- The wrapped DataFrame is never mutated; each operation returns a new Wrap

### Validation ideas

- `Wrap(df).where("x > 1")` returns Wrap with filtered rows
- Chain: `w.where(...).project(...).take(5)` produces correct result
- `w.df` is the expected DataFrame
- `w.execute("self | ...")` works with any KQL pipeline

## FR-23: Jupyter magic commands (adxpandas)

adxpandas must provide IPython/Jupyter magic commands for interactive KQL querying.

### Rationale

Notebooks are a primary use case. Magic commands let users write KQL directly in cells without Python boilerplate.

### Expected behavior

- `import adxpandas.magic` registers the `%kql` and `%%kql` magic
- Line magic: `%kql df | where x > 1 | take 5` — executes against local-scope DataFrames
- Cell magic: `%%kql\ndf | where x > 1` — multi-line queries
- Variables in the local and global namespace that are DataFrames or Wraps are available as table names
- Returns `Wrap` (displayable in notebook) or `RenderResult` (if query ends with render)
- Result can be captured: `result = %kql df | where x > 1`
- IPython is a lazy import; `import adxpandas` must succeed without IPython installed
- If IPython is not available when importing `adxpandas.magic`, raise a clear ImportError

### Validation ideas

- Magic returns correct filtered DataFrame
- Multiple DataFrames in namespace can be referenced
- Wrap objects in namespace are usable as tables
- Missing IPython raises clear error

## FR-24: `render` operator chart visualization (adxpandas)

adxpandas must support the KQL `render` operator for chart visualization.

### Rationale

KQL's `render` operator is a standard way to visualize query results. Supporting it allows users to produce charts from their queries without separate plotting code.

### Supported visualization types

| Type | Chart | Description |
|------|-------|-------------|
| `timechart` | Line chart | Time series with datetime x-axis |
| `linechart` | Line chart | General line chart |
| `barchart` | Horizontal bar | Horizontal bar chart |
| `columnchart` | Vertical bar | Vertical bar chart |
| `piechart` | Pie chart | Proportional display |
| `areachart` | Area chart | Filled line chart |
| `table` | Table figure | Tabular display |

### Supported syntax

```
T | ... | render visualization [with (xcolumn=col, ycolumns=col1, title="...")]
```

### Expected behavior

- `render` must be the **terminal** operator in a pipeline (nothing follows it)
- `render` is a **display directive**, not a data transformation — it does not change the DataFrame
- The executor ignores RenderOp during execution (no effect on data pipeline)
- When detected by Wrap or magic, the result is a `RenderResult` object
- `RenderResult` has a `.df` property for the raw data and `.figure` for the matplotlib figure
- `RenderResult._repr_html_()` embeds the chart as PNG in notebooks
- matplotlib is a lazy import; render raises ImportError with install instructions if missing
- `AdxPandasClient.query()` always returns a DataFrame (render is ignored at that level)
- Wrap `.render()` method creates a RenderResult directly (without query string)

### Design constraints

- RenderOp is modeled as an Operator AST node for parser consistency
- The parser accepts render anywhere in the pipeline position but semantically it should be terminal
- `with (...)` properties are optional and parsed as key=value pairs
- Default xcolumn is the first column; default ycolumns are all remaining columns

### Validation ideas

- `T | summarize count() by city | render barchart` parses correctly
- Executor produces correct DataFrame (render doesn't alter data)
- `Wrap.execute("self | ... | render timechart")` returns RenderResult
- `Wrap.render("barchart")` returns RenderResult
- Missing matplotlib gives clear ImportError
- `render` with `with (xcolumn=time, title="My Chart")` parses properties
