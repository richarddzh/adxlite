# Architecture

This document explains how AdxLite is structured internally and how a KQL statement moves from raw text to a pandas DataFrame result. The focus is on implementation architecture rather than user-facing syntax. For public API usage, see [API reference](../reference/api.md). For language details, see [KQL syntax](../reference/kql-syntax.md), [Operators](../reference/operators.md), and [Functions](../reference/functions.md).

## Monorepo structure

The repository contains two Python packages:

- **adxpandas** — standalone KQL-over-pandas execution (no database)
- **adxlite** — SQLite-backed KQL execution (depends on adxpandas)

```text
repo_root/
├── adxpandas/              # Sub-project: pure pandas KQL engine
│   ├── pyproject.toml
│   ├── src/adxpandas/
│   │   ├── parser/         # Shared KQL parser (tokenizer, AST, parser)
│   │   ├── engine/         # Pandas execution engine
│   │   ├── functions.py    # Pure-Python KQL function implementations
│   │   ├── client.py       # AdxPandasClient API
│   │   ├── wrap.py         # Wrap class (single-DataFrame quick query)
│   │   ├── magic.py        # Jupyter %kql magic (optional, requires IPython)
│   │   ├── render.py       # Chart rendering (optional, requires matplotlib)
│   │   └── exceptions.py   # Base exceptions
│   └── tests/
├── adxlite/                # Main project: SQLite-backed KQL engine
│   ├── pyproject.toml
│   ├── src/adxlite/
│   │   ├── parser/         # Shim modules re-exporting from adxpandas
│   │   ├── engine/         # SQLite+pandas hybrid execution
│   │   ├── translator/     # AST-to-SQL translation (SQLite-specific)
│   │   ├── storage/        # SQLite database layer
│   │   ├── client.py       # AdxLiteClient API
│   │   └── exceptions.py   # Re-exports + SQLite-specific exceptions
│   └── tests/
├── docs/                   # Shared documentation
├── mkdocs.yml
└── README.md
```

## Architectural goals

AdxLite is built around a small set of goals:

- keep execution local and dependency-light by embedding SQLite
- expose a compact Python API suitable for scripts, tests, and notebooks
- support a practical subset of KQL rather than the full Azure Data Explorer surface area
- preserve predictable pipeline semantics even when multiple KQL operators are chained
- use pandas where it provides meaningfully better ergonomics than raw SQL
- keep type behavior explicit through schema metadata rather than relying only on SQLite affinity

## Module map

The codebase is organized under `src/adxlite/`.

```text
src/adxlite/
├── __init__.py
├── client.py
├── exceptions.py
├── parser/
│   ├── tokenizer.py
│   ├── ast_nodes.py
│   └── parser.py
├── translator/
│   ├── translator.py
│   ├── functions.py
│   └── sql_utils.py
├── storage/
│   ├── database.py
│   ├── kql_types.py
│   └── udf.py
└── engine/
    ├── planner.py
    ├── executor.py
    └── pandas_ops.py
```

## Dependency diagram

The following diagram shows the primary runtime dependencies between modules.

```text
AdxLiteClient (client.py)
    |
    v
ExecutionEngine (engine/executor.py)
    |-------------------------------> Database (storage/database.py)
    |                                     |
    |                                     +--> kql_types.py
    |                                     +--> udf.py
    |
    +--> parse_kql (parser/parser.py)
    |       |
    |       +--> tokenizer.py
    |       +--> ast_nodes.py
    |
    +--> Planner (engine/planner.py)
    |       |
    |       +--> Database.get_schema()
    |       +--> ast_nodes.py
    |
    +--> SqlTranslator (translator/translator.py)
    |       |
    |       +--> translator/functions.py
    |       +--> translator/sql_utils.py
    |       +--> ast_nodes.py
    |
    +--> PandasOperatorExecutor (engine/pandas_ops.py)
            |
            +--> storage/udf.py
            +--> ast_nodes.py
```

## Layer responsibilities

### Public API layer

`client.py` contains `AdxLiteClient`, the only class most users need.

Responsibilities:

- open a database connection through `Database`
- expose simple methods for ingest, query, table listing, schema inspection, dropping tables, and closing resources
- hide parser, planner, translator, and execution details behind a stable interface
- support context manager usage for deterministic cleanup

This layer deliberately stays thin. It is an orchestration layer, not a business-logic layer.

### Parser layer

The parser layer is split into three modules:

- `tokenizer.py`: raw text to token stream
- `ast_nodes.py`: immutable syntax tree structures
- `parser.py`: recursive-descent parsing from tokens into AST nodes

Responsibilities:

- recognize table names, operators, literals, and expressions
- normalize supported keywords into a stable AST representation
- reject unsupported syntax early with `KqlParseError` or `KqlUnsupportedError`
- produce either a `Pipeline` or an `AppendCommand`

The parser understands KQL as a pipeline language: a source table followed by zero or more pipe operators.

### Planning layer

`engine/planner.py` bridges parsing and execution.

Responsibilities:

- verify that the source table exists
- fetch the current table schema from metadata
- rewrite `project-away` into a positive projection based on known columns
- infer output schema after each operator
- split a pipeline into a SQL-compatible prefix and a pandas-only suffix

Today, the split is simple: everything is SQL-compatible except `parse`. The design is still important because it creates an explicit boundary for hybrid execution.

### Translation layer

`translator/translator.py` converts SQL-compatible AST nodes into SQLite SQL plus parameter values.

Responsibilities:

- turn the source table into `SELECT * FROM "Table"`
- wrap each pipeline stage in a nested subquery to preserve operator ordering
- map KQL scalar functions to SQLite expressions or SQLite UDF calls
- translate aggregates into SQL aggregate expressions
- bind literal values as SQL parameters rather than interpolating them into SQL text

`translator/functions.py` contains the function-rendering registry used by the translator. `translator/sql_utils.py` contains small helpers such as identifier quoting.

### Storage layer

The storage layer centers on `storage/database.py`.

Responsibilities:

- own the SQLite connection
- register UDFs on the connection
- create and maintain internal metadata tables
- create user tables during ingestion
- normalize DataFrame values for storage
- execute SQL and restore result columns according to KQL schema metadata

`storage/kql_types.py` handles type inference, normalization, and result restoration. `storage/udf.py` implements SQLite UDFs used by translated SQL and by pandas fallback execution.

### Execution layer

The execution layer has two main modules:

- `engine/executor.py`: top-level orchestration
- `engine/pandas_ops.py`: pandas-side operator execution

Responsibilities:

- parse KQL text
- recognize `.append` management commands
- invoke the planner and translator
- execute generated SQL through `Database`
- apply any pandas operators to the SQL result DataFrame
- normalize final datetime columns for the result

## End-to-end execution pipeline

```text
KQL text
  |
  v
Tokenizer
  |
  v
Tokens
  |
  v
Recursive-descent parser
  |
  v
AST (Pipeline or AppendCommand)
  |
  v
Planner
  |
  +--> resolves project-away
  +--> infers schemas
  +--> splits SQL and pandas phases
  |
  v
SQL-compatible pipeline + pandas operator suffix
  |
  v
SQL translator
  |
  v
SQLite SQL + parameters
  |
  v
Database.query_dataframe()
  |
  v
Initial pandas DataFrame result
  |
  v
PandasOperatorExecutor (if needed)
  |
  v
Final pandas DataFrame
```

## Query flow: pure SQL pipeline

A pure SQL pipeline is any pipeline whose operators are all SQL-compatible.

Example:

```kql
Users
| where score >= 20
| extend doubled = score * 2
| summarize total=count(), max_score=max(score) by city
| sort by total desc
```

Execution flow:

1. `parse_kql()` turns the query into a `Pipeline` AST.
2. `Planner.plan()` confirms the table exists and infers output schema after each operator.
3. Because none of the operators require pandas, the pandas suffix is empty.
4. `SqlTranslator.translate()` produces nested SQL statements plus bound parameters.
5. `Database.query_dataframe()` executes the SQL and restores result types such as booleans and datetimes where schema information is available.
6. The result is returned directly to the caller.

Benefits of the pure SQL path:

- minimal data transfer between SQLite and pandas
- faster execution for filters, projections, aggregates, and sorts
- leverages SQLite indexes if added outside AdxLite

## Query flow: hybrid SQL + pandas pipeline

A hybrid pipeline is used when at least one operator cannot be expressed in the SQL subset used by AdxLite. Today the main example is `parse`.

Example:

```kql
Logs
| where Message matches regex "login|logout"
| parse Message with "user=" user " action=" action
| project user, action
```

Execution flow:

1. The parser returns a `Pipeline` AST containing `WhereOp`, `ParseOp`, and `ProjectOp`.
2. The planner walks the operators in order.
3. `where` is SQL-compatible and stays in the SQL prefix.
4. `parse` is not SQL-compatible, so the planner marks a split point.
5. `parse` and all following operators become the pandas suffix.
6. SQL executes first and returns a DataFrame containing only the rows that passed the filter.
7. `PandasOperatorExecutor` applies `parse` by building a regular expression from the parse pattern and extracting capture columns.
8. Remaining pandas-side operators such as `project` operate on that DataFrame.
9. The final DataFrame is returned to the caller.

Why the suffix includes all later operators:

- later operators may depend on columns created by `parse`
- a single split point keeps execution order easy to reason about
- it avoids repeated back-and-forth conversion between SQLite and pandas

## Management command flow: `.append`

AdxLite supports one management-style command:

```kql
.append Archive <| Source | where ok == true
```

Execution flow:

1. The parser returns an `AppendCommand`, not a normal `Pipeline`.
2. `ExecutionEngine.execute()` recognizes the command.
3. The nested query is executed as a normal pipeline.
4. The resulting DataFrame is ingested into the target table in `append` mode.
5. The command returns an empty DataFrame to the caller.

This architecture reuses the same planner, translator, and executor path for both query-only and query-then-write workflows.

## Storage model

AdxLite stores data in ordinary SQLite user tables plus one internal metadata table.

### User tables

Each ingested DataFrame becomes a SQLite table whose name matches the supplied table name. Column storage types are chosen from the inferred logical KQL schema.

### Metadata table

`Database` maintains an internal table named `__adxlite_columns`.

Columns:

| Column | Meaning |
| --- | --- |
| `table_name` | User table name |
| `column_name` | Logical column name |
| `ordinal` | Original column order from ingestion |
| `kql_type` | Logical KQL type such as `long`, `string`, or `datetime` |

Why the metadata exists:

- SQLite storage affinity alone is not enough to preserve KQL intent
- datetime columns are stored as text but should be restored as pandas datetimes
- append validation needs a reliable logical schema
- user table order must remain stable for schema inspection and append checks

## Datetime data path

Datetime handling is a cross-cutting architectural concern.

1. `kql_types.infer_column_type()` detects pandas datetime dtypes.
2. `normalize_for_storage()` converts each value to ISO-8601 text before insertion.
3. SQLite stores the value in a `TEXT` column.
4. Query functions such as `bin`, `ago`, `now`, and `datetime_add` operate through UDFs that parse and re-emit ISO-8601 strings.
5. `restore_series()` converts result columns marked as `datetime` back to pandas datetime dtype.

This choice keeps storage simple while preserving enough semantics for comparison, sorting, and bucketing.

## Operator compatibility by layer

| Operator | Parser | Planner | SQLite SQL | Pandas fallback |
| --- | --- | --- | --- | --- |
| `where` | yes | yes | yes | yes |
| `project` | yes | yes | yes | yes |
| `project-away` | yes | resolved to `project` | indirectly | yes |
| `extend` | yes | yes | yes | yes |
| `summarize` | yes | yes | yes | yes |
| `take` / `limit` | yes | yes | yes | yes |
| `count` | yes | yes | yes | yes |
| `sort by` / `order by` | yes | yes | yes | yes |
| `top` | yes | yes | yes | yes |
| `distinct` | yes | yes | yes | yes |
| `parse` | yes | yes | no | yes |

## Error propagation model

Errors are intentionally categorized by architectural stage.

| Stage | Typical exception |
| --- | --- |
| Tokenization or parsing | `KqlParseError` |
| Valid but unsupported syntax | `KqlUnsupportedError` |
| Missing table | `TableNotFoundError` |
| Append schema mismatch | `SchemaError` |
| SQL translation problem | `TranslationError` |
| SQLite execution problem | `ExecutionError` |

This separation is useful in application code because callers can decide whether a failure should be shown as a user syntax issue, a product limitation, or a storage/runtime problem.

## Why the architecture is intentionally simple

AdxLite is not trying to implement a full optimizer or distributed execution stack. The architecture favors clarity and correctness over maximum abstraction.

Examples of intentional simplicity:

- one embedded database engine: SQLite
- one public client class: `AdxLiteClient`
- one explicit planner split between SQL and pandas
- one metadata table for logical schema tracking
- one AST model shared across parser, planner, translator, and pandas execution

## Related documents

- [Design decisions](decisions.md) explains *why* these architectural choices were made.
- [Type system](type-system.md) explains how schemas move between pandas, SQLite, and KQL.
- [Requirements](requirements.md) lists the functional requirements this architecture serves.
- [API reference](../reference/api.md) documents the public surfaces that sit on top of this design.
