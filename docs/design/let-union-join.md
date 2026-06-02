# Design: let, union, join Support

## Overview

This document describes the design for adding `let`, `union`, and `join` support to adxlite. These are the three most impactful KQL features that were previously unsupported.

---

## 1. `let` Statement

### KQL Semantics (from Kusto source)

`let` binds a name to a value. Three forms exist:

```kql
// Scalar binding
let threshold = 100;
T | where value > threshold

// Tabular binding
let errors = T | where level == "error";
errors | summarize count() by source

// Function binding (NOT supported in adxlite)
let f = (x: int) { x * 2 };
```

**Scoping rules** (from `Binder_Names.cs`):
- Column/row-scope names **win over** let variables
- Let bindings are visible to all subsequent statements
- A tabular let can reference earlier scalar lets

### adxlite Design

#### Supported Forms

| Form | Support | Notes |
|------|---------|-------|
| Scalar let (`let x = expr;`) | ✅ | Numeric, string, timespan, datetime literals and simple expressions |
| Tabular let (`let t = pipeline;`) | ✅ | Execute pipeline, store as temp table |
| Function let (`let f = (params) {...}`) | ❌ | Too complex for MVP, raise `KqlUnsupportedError` |

#### AST Representation

```python
@dataclass(frozen=True)
class LetBinding:
    name: str
    value: Expr | Pipeline  # scalar expression or tabular pipeline

@dataclass(frozen=True)
class KqlStatement:
    let_bindings: tuple[LetBinding, ...]
    body: Pipeline | UnionPipeline | AppendCommand
```

#### Parser Changes

- Add `SEMICOLON` token type
- Add `let` to `KEYWORDS`
- Top-level parse: consume `let name = ...; ` bindings until a non-let statement is found
- Scalar let: `let name = expression ;` (expression does NOT start with a table name followed by `|`)
- Tabular let: `let name = tableName | operators... ;`
- Disambiguation: If the value starts with an identifier followed by `|`, it's tabular; otherwise scalar

#### Execution Strategy

1. **Scalar lets**: Build a `bindings: dict[str, object]` context
   - During expression evaluation, if an `Identifier` is not a column name, look it up in bindings
   - Substitute as a literal value in SQL parameters
   
2. **Tabular lets**: 
   - Execute the sub-pipeline to get a DataFrame
   - Store as a SQLite temp table (`CREATE TEMP TABLE _let_{name} AS ...` or use `ingest_dataframe` with a temp prefix)
   - Register in a `QueryContext` so `table_exists()` and `get_schema()` resolve it
   - Clean up temp tables after the main query completes (use `try/finally`)

#### Scoping Rules (matching Kusto)

- Column names in the current table schema take precedence over scalar let names
- Let bindings are resolved top-to-bottom; later lets can reference earlier ones
- If a let name collides with a table name, the let wins (tabular let shadows the real table)

---

## 2. `union` Operator

### KQL Semantics (from Kusto source)

Union combines rows from multiple tables.

```kql
// As source
union T1, T2, T3 | where value > 10

// As pipe operator
T1 | union T2, T3

// With options
union kind=inner T1, T2           // only common columns
union kind=outer withsource=src T1, T2  // all columns + source indicator
```

**Parameters** (from `QueryOperatorParameters.cs`):
- `kind=inner|outer` — inner keeps only common columns, outer keeps all (default: outer)
- `withsource=ColumnName` — adds a column with source table name
- `isfuzzy` — not relevant for local execution

**Schema alignment** (from `Binder_NodeBinder.cs`):
- Result schema is unified by column name and type across all inputs
- Columns missing in a table become NULL in the result
- `kind=inner`: only columns present in ALL inputs are kept

### adxlite Design

#### Supported Forms

| Form | Support | Notes |
|------|---------|-------|
| `union T1, T2, T3 \| ...` (as source) | ✅ | |
| `T1 \| union T2, T3` (as pipe) | ✅ | Left side is current result, union with named tables |
| `kind=inner` | ✅ | Only common columns |
| `kind=outer` (default) | ✅ | All columns, NULL for missing |
| `withsource=col` | ✅ | Adds source name column |
| Union with sub-pipelines | ❌ MVP | Only table names for now |

#### AST Representation

```python
@dataclass(frozen=True)
class UnionOp(Operator):
    """Union as pipe operator: T1 | union T2, T3."""
    tables: tuple[str, ...]
    kind: str = "outer"          # "inner" or "outer"
    withsource: str | None = None

@dataclass(frozen=True)
class UnionSource:
    """Union as a source: union T1, T2 | ..."""
    tables: tuple[str, ...]
    kind: str = "outer"
    withsource: str | None = None

@dataclass(frozen=True)
class UnionPipeline:
    """Pipeline starting with union source."""
    source: UnionSource
    operators: tuple[Operator, ...] = ()
```

#### SQL Translation Strategy

For `kind=outer` (default), compute the superset of columns across all tables:

```sql
SELECT col1, col2, col3, NULL AS col4 FROM T1
UNION ALL
SELECT col1, col2, NULL AS col3, col4 FROM T2
```

For `kind=inner`, compute the intersection of columns:

```sql
SELECT col1, col2 FROM T1
UNION ALL
SELECT col1, col2 FROM T2
```

For `withsource`:
```sql
SELECT 'T1' AS [source_col], col1, col2 FROM T1
UNION ALL
SELECT 'T2' AS [source_col], col1, col2 FROM T2
```

#### Schema Resolution

1. Query schema for each table in the union
2. Compute output columns:
   - `kind=outer`: union of all column names (ordered: first table's columns first, then new ones from subsequent tables)
   - `kind=inner`: intersection of all column names
3. Generate SELECT for each table with explicit column list (NULL for missing)

---

## 3. `join` Operator

### KQL Semantics (from Kusto source)

Join combines columns from two tables based on matching keys.

```kql
// Simple join on common column
T1 | join T2 on key

// With kind
T1 | join kind=leftouter T2 on key

// Multi-key
T1 | join T2 on key1, key2

// Qualified keys
T1 | join T2 on $left.id == $right.user_id

// Right side is a sub-pipeline
T1 | join kind=inner (T2 | where active == true) on id
```

**Join kinds** (from `KustoFacts.cs`):

| Kind | SQLite Equivalent | Output |
|------|-------------------|--------|
| `innerunique` (default) | INNER JOIN (deduplicate right) | Left + right columns |
| `inner` | INNER JOIN | Left + right columns |
| `leftouter` | LEFT JOIN | Left + right columns |
| `rightouter` | *swap + LEFT JOIN* | Left + right columns |
| `fullouter` | *LEFT + UNION + unmatched right* | Left + right columns |
| `leftanti` / `leftantisemi` | WHERE NOT EXISTS | Left columns only |
| `rightsemi` | WHERE EXISTS (swap) | Right columns only |
| `leftsemi` | WHERE EXISTS | Left columns only |
| `rightanti` / `rightantisemi` | WHERE NOT EXISTS (swap) | Right columns only |

**On clause** (from `Binder_NodeBinder.cs`):
- Simple form: `on col` — column exists in both sides
- Qualified form: `on $left.a == $right.b`
- Multiple keys: `on col1, col2` or `on $left.a == $right.b, $left.c == $right.d`

**Output column rules** (from `Binder_NodeBinder.cs`):
- Join key columns (simple form): appear once in output (not duplicated)
- Non-key columns from both sides are included
- If both sides have a non-key column with same name → right-side gets `_right` suffix (Kusto actually uses `$right_colname` but we'll use `right_colname`)
- Anti/semi joins only output one side's columns

### adxlite Design

#### Supported Forms

| Form | Support | Notes |
|------|---------|-------|
| `join kind=inner` | ✅ | |
| `join kind=leftouter` | ✅ | |
| `join kind=innerunique` (default) | ✅ | Same as inner for MVP (dedup not implemented initially) |
| `join kind=leftanti` | ✅ | Via NOT EXISTS |
| `join kind=leftsemi` | ✅ | Via EXISTS |
| `join kind=rightouter` | ✅ | Swap sides + LEFT JOIN |
| `join kind=rightanti` | ✅ | Swap + NOT EXISTS |
| `join kind=rightsemi` | ✅ | Swap + EXISTS |
| `join kind=fullouter` | ✅ | LEFT JOIN UNION unmatched right |
| Simple on: `on col` | ✅ | |
| Qualified on: `on $left.a == $right.b` | ✅ | |
| Multi-key: `on col1, col2` | ✅ | |
| Right side as sub-pipeline | ✅ | Translated recursively |

#### AST Representation

```python
@dataclass(frozen=True)
class JoinCondition:
    """A single join key pair."""
    left_column: str
    right_column: str

@dataclass(frozen=True)
class JoinOp(Operator):
    """Join operator."""
    kind: str  # inner, leftouter, rightouter, fullouter, leftanti, leftsemi, rightsemi, rightanti, innerunique
    right: Pipeline  # the right-side sub-pipeline
    conditions: tuple[JoinCondition, ...]
```

#### Parser Changes

- Add `$` token handling → when followed by `left` or `right`, produce a `QualifiedIdentifier`
- Parse: `join [kind=X] ( pipeline ) on condition [, condition]*`
- Condition parsing:
  - Simple: identifier → `JoinCondition(col, col)`
  - Qualified: `$left.a == $right.b` → `JoinCondition("a", "b")`

#### SQL Translation Strategy

**Inner join:**
```sql
SELECT _l.*, _r.col3, _r.col4
FROM ({left_sql}) AS _l
INNER JOIN ({right_sql}) AS _r
ON _l.[key] = _r.[key]
```

**Left outer:**
```sql
SELECT _l.*, _r.col3, _r.col4
FROM ({left_sql}) AS _l
LEFT JOIN ({right_sql}) AS _r
ON _l.[key] = _r.[key]
```

**Left anti (NOT EXISTS):**
```sql
SELECT _l.*
FROM ({left_sql}) AS _l
WHERE NOT EXISTS (
    SELECT 1 FROM ({right_sql}) AS _r
    WHERE _l.[key] = _r.[key]
)
```

**Left semi (EXISTS):**
```sql
SELECT _l.*
FROM ({left_sql}) AS _l
WHERE EXISTS (
    SELECT 1 FROM ({right_sql}) AS _r
    WHERE _l.[key] = _r.[key]
)
```

**Right outer / right anti / right semi:**
Swap left and right, use the corresponding left-variant.

**Full outer (SQLite workaround):**
```sql
SELECT _l.*, _r.col3
FROM ({left_sql}) AS _l
LEFT JOIN ({right_sql}) AS _r ON _l.[key] = _r.[key]
UNION ALL
SELECT NULL, NULL, ..., _r.*
FROM ({right_sql}) AS _r
WHERE NOT EXISTS (
    SELECT 1 FROM ({left_sql}) AS _l
    WHERE _l.[key] = _r.[key]
)
```

#### Output Column Naming

1. Join key columns (simple form): appear once, from left side
2. Left non-key columns: keep original names
3. Right non-key columns: if name conflicts with left, suffix with `_right`
4. Anti/semi joins: only left columns (or right for right-variants)

---

## 4. Execution Engine Changes

### QueryContext

A new `QueryContext` class carries state through query execution:

```python
@dataclass
class QueryContext:
    scalar_bindings: dict[str, object]  # let x = 5
    table_bindings: dict[str, str]      # let name → temp table name
    temp_tables: list[str]              # for cleanup
```

### Execution Flow with `let`

```
parse KqlStatement
  → resolve let bindings top-to-bottom:
    - scalar: add to context.scalar_bindings
    - tabular: execute sub-pipeline, create temp table, add to context.table_bindings
  → execute body pipeline with context
  → cleanup temp tables (try/finally)
```

### Planner Changes

- `JoinOp` is SQL-compatible (can be translated to JOIN SQL)
- `UnionOp` is SQL-compatible (UNION ALL)
- Both need access to database schema for the right/union tables
- Planner receives `QueryContext` to resolve let-bound table names

---

## 5. Implementation Phases

| Phase | Scope | Risk |
|-------|-------|------|
| 1 | Scalar `let` | Low — simple substitution |
| 2 | `union` (source + pipe, kind=outer/inner, withsource) | Medium — schema alignment |
| 3 | `join` (inner, leftouter) with simple on | Medium — SQL generation complexity |
| 4 | `join` (anti, semi variants) | Low — EXISTS pattern |
| 5 | Tabular `let` | Medium — temp table lifecycle |
| 6 | `join` (fullouter, rightouter) | Low — composition of simpler patterns |
| 7 | `join` with qualified $left/$right keys | Low — parser extension |
| 8 | Pandas fallback for union/join after parse | Low — mirror SQL logic in pandas |

---

## 6. Limitations

- **No function lets** — `let f = (x) { ... }` is not supported
- **No union with sub-pipelines** — `union (T1 | where x > 5), T2` requires nested parsing (future)
- **innerunique** — treated same as inner (no automatic right-side deduplication)
- **Cross-database join** — still not supported (all tables must be in the same local database)
- **Union/join after pandas-only operators** — requires pandas-side implementation (Phase 8)

---

## 7. Test Plan

### `let` tests
- Scalar let with number, string, timespan
- Scalar let used in where, extend, summarize
- Multiple scalar lets referencing each other
- Tabular let + subsequent query
- Column name shadows let name (column wins)
- Undefined let name → error

### `union` tests
- Two tables, same schema → simple union
- Two tables, different schemas → NULL fill (kind=outer)
- kind=inner → only common columns
- withsource → source column added
- Union as source vs pipe operator → same result
- Union with empty table
- Union followed by where/summarize

### `join` tests
- Inner join on single key
- Left outer join → NULL for unmatched
- Left anti → only non-matching left rows
- Left semi → left rows that have match
- Multi-key join
- Qualified keys ($left.a == $right.b)
- Column name conflict → _right suffix
- Join with right-side sub-pipeline (where filter)
- Join on empty tables
- Right outer / right anti / right semi
- Full outer join
