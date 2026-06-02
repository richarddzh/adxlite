# AdxLite Documentation

Welcome to the AdxLite documentation set. This documentation is written for Python developers who want local analytics with KQL-style queries, but who may not be familiar with Azure Data Explorer internals. Every page is designed to be self-contained, with explanations, examples, and references to related sections.

AdxLite combines four ideas:

1. pandas DataFrames as the primary ingestion and result format
2. SQLite as the local storage engine
3. a parser and translator for a practical subset of KQL
4. pandas post-processing for features that are awkward to express in SQL alone

Use this index as the main table of contents for the project.

## Documentation roadmap

If you are brand new to AdxLite, read the documents in this order:

1. Project README (in repository root) for the project overview and installation summary
2. [Quickstart](guides/quickstart.md) for the first successful ingest and query
3. [Ingestion guide](guides/ingestion.md) for table creation, append mode, and schema behavior
4. [Advanced queries](guides/advanced-queries.md) for parse, datetime, JSON, and aggregation patterns
5. [API reference](reference/api.md) when you are ready to integrate AdxLite into application code

If you are evaluating the implementation or planning changes, continue with:

6. [Architecture](design/architecture.md)
7. [Design decisions](design/decisions.md)
8. [Type system](design/type-system.md)
9. [Requirements](design/requirements.md)
10. [KQL syntax](reference/kql-syntax.md)
11. [Functions](reference/functions.md)
12. [Operators](reference/operators.md)
13. [Limitations](reference/limitations.md)

## High-level map

| Area | Document | What you will learn |
| --- | --- | --- |
| Overview | Project README (repo root) | What AdxLite is, why it exists, how to install it, and where to go next |
| Index | [This page](index.md) | The full documentation map and recommended reading order |
| Getting started | [Quickstart](guides/quickstart.md) | Create a client, load a DataFrame, run your first KQL query, and choose between file-backed and in-memory storage |
| Data loading | [Ingestion guide](guides/ingestion.md) | Ingest APIs, replace vs append semantics, schema metadata, type inference, and large dataset considerations |
| Query patterns | [Advanced queries](guides/advanced-queries.md) | Practical KQL pipelines, parse usage, datetime bucketing, regex extraction, JSON access, and `.append` workflows |
| Internals | [Architecture](design/architecture.md) | Module boundaries, execution pipeline, planner behavior, hybrid execution, and metadata storage |
| Tradeoffs | [Design decisions](design/decisions.md) | Why the project uses SQLite, UDFs, hybrid execution, nested subqueries, ISO-8601 datetimes, and parameterized SQL |
| Types | [Type system](design/type-system.md) | Type mappings between KQL, SQLite, and pandas, including datetime and dynamic handling |
| Requirements | [Requirements](design/requirements.md) | The complete functional requirement set used to scope the project |
| Syntax | [KQL syntax](reference/kql-syntax.md) | Grammar overview, literals, identifiers, expressions, pipeline syntax, and case rules |
| Functions | [Functions reference](reference/functions.md) | Every implemented function with signature, parameters, return type, examples, and notes |
| Operators | [Operators reference](reference/operators.md) | All supported operators and predicates with semantics, examples, and caveats |
| Limits | [Limitations](reference/limitations.md) | Unsupported KQL surface area, behavioral differences from Kusto, and workarounds |
| Python API | [API reference](reference/api.md) | `AdxLiteClient`, exceptions, context manager behavior, and parser entry points |

## Choosing the right document

### I want to get something working quickly

Start with [Quickstart](guides/quickstart.md). It walks through installation, database creation, ingestion, query execution, and context manager usage. It also includes copy-and-paste examples for the most common operators.

### I already know KQL but need to know what subset is available

Read [KQL syntax](reference/kql-syntax.md), [Operators reference](reference/operators.md), and [Functions reference](reference/functions.md). Then read [Limitations](reference/limitations.md) to understand what is intentionally out of scope.

### I know Python and pandas, but not KQL

Read [Quickstart](guides/quickstart.md) first, then [Advanced query patterns](guides/advanced-queries.md). Those pages explain KQL as a pipeline language rather than assuming prior Kusto experience.

### I need to load DataFrames reliably in production code

Read [Ingestion guide](guides/ingestion.md) and [Type system](design/type-system.md). Together they explain schema inference, datetime storage, append validation, and what values are restored on query output.

### I need to understand how the engine actually works

Read [Architecture](design/architecture.md) and [Design decisions](design/decisions.md). Those pages explain the parser, AST, planner, SQL translator, SQLite UDF layer, and pandas fallback path.

## Core concepts used throughout the docs

The same terminology appears across the documentation set.

| Term | Meaning in AdxLite |
| --- | --- |
| Client | The public `AdxLiteClient` object that application code uses |
| Pipeline | A KQL query made of a source table and a sequence of pipe operators |
| SQL-compatible stage | The prefix of a pipeline that can be translated entirely into SQLite SQL |
| Pandas stage | The suffix of a pipeline that must execute in pandas, currently used for `parse` |
| KQL schema | The logical column type mapping stored in metadata, separate from raw SQLite type names |
| Dynamic | JSON-shaped data represented as text in storage and typically as JSON strings in query results |
| Timespan | A duration literal such as `1d` or `30m` interpreted by UDFs |

## Quick capability summary

AdxLite supports:

- local SQLite database files and in-memory databases
- DataFrame ingestion and query results as pandas DataFrames
- KQL pipelines with `let`, `union`, `join`, and standard tabular operators
- aggregate functions, string helpers, datetime helpers, and JSON helpers
- `datetime(...)` literals and ISO-8601 datetime storage
- `.append TableName <| query`
- empty-table aggregation semantics for `count()`

AdxLite does not support:

- external Kusto clusters
- multi-database or cross-engine joins
- the full Azure Data Explorer operator catalog
- distributed execution or cluster management features

## Cross-reference guide

These pairs of documents are often useful together:

- [Quickstart](guides/quickstart.md) + [API reference](reference/api.md)
- [Ingestion guide](guides/ingestion.md) + [Type system](design/type-system.md)
- [Advanced queries](guides/advanced-queries.md) + [Functions reference](reference/functions.md)
- [Architecture](design/architecture.md) + [Design decisions](design/decisions.md)
- [KQL syntax](reference/kql-syntax.md) + [Operators reference](reference/operators.md)
- [Operators reference](reference/operators.md) + [Limitations](reference/limitations.md)

## Reading tips

- If you need exact API signatures, prefer the reference pages over guides.
- If you need examples, prefer the guides first.
- If you need to understand behavior differences from Azure Data Explorer, always check [Limitations](reference/limitations.md).
- If you are debugging type behavior, consult [Type system](design/type-system.md) before reading the source.

## Conventions used in the docs

- KQL snippets use pipe syntax and assume a single source table.
- Python snippets assume `import pandas as pd` and `from adxlite import AdxLiteClient` unless stated otherwise.
- Return values shown as DataFrames are representative rather than guaranteed display formatting.
- Types are described in three layers when relevant: KQL logical type, SQLite storage type, and pandas runtime representation.

## Where to go next

- New user: go to [Quickstart](guides/quickstart.md)
- Existing pandas user: go to [Ingestion guide](guides/ingestion.md)
- Existing KQL user: go to [Operators reference](reference/operators.md)
- Maintainer or contributor: go to [Architecture](design/architecture.md)

## Documentation maintenance notes

This documentation intentionally describes the current implementation, not an aspirational API. When behavior differs from real Kusto, the docs call that out explicitly. If you extend AdxLite, update both the relevant guide and at least one reference page so that the documentation remains self-sufficient.
