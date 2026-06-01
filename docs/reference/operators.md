# Operators Reference

This reference documents the operators supported by AdxLite. It covers both tabular pipeline operators and expression-level comparison or predicate operators. For grammar details, see [KQL syntax](kql-syntax.md). For function signatures, see [Functions reference](functions.md).

## Reading this reference

Each section includes:

- syntax
- description
- parameter notes
- examples
- implementation notes or caveats when relevant

## Tabular operators

## `where`

**Syntax**

```kql
Table | where predicate
```

**Description**

Filters rows using a boolean expression.

**Parameters**

| Parameter | Type | Description |
| --- | --- | --- |
| `predicate` | expression returning bool | Row-level condition evaluated against each input row |

**Examples**

```kql
Users | where score >= 10
Users | where city == "London" and ok == true
Users | where ts >= ago(1d)
```

**Notes**

- `where` is SQL-compatible and therefore stays in the SQLite path unless it appears after a pandas-only split point such as `parse`
- null handling follows SQLite or pandas expression semantics depending on execution path

## `project`

**Syntax**

```kql
Table | project expr1, alias2 = expr2, ...
```

**Description**

Selects a new column list and optionally renames or computes columns.

**Parameters**

| Parameter | Type | Description |
| --- | --- | --- |
| `expr` | expression | Expression to include in the output |
| `alias` | identifier | Optional explicit output column name |

**Examples**

```kql
Users | project name, score
Users | project user_name = name, doubled = score * 2
Users | project city, hour_bucket = bin(ts, 1h)
```

**Notes**

- columns not listed are removed from the output
- explicit aliases are recommended for readability when projecting expressions

## `project-away`

**Syntax**

```kql
Table | project-away col1, col2, ...
```

**Description**

Removes named columns and keeps all others.

**Parameters**

| Parameter | Type | Description |
| --- | --- | --- |
| `col1`, `col2`, ... | identifier | Columns to remove |

**Examples**

```kql
Users | project-away payload
Logs | project-away Message, raw_json
```

**Notes**

- internally the planner rewrites `project-away` into a positive `project` using the current schema
- if the schema has already changed earlier in the pipeline, the removal list applies to the current shape, not the original table shape

## `extend`

**Syntax**

```kql
Table | extend alias = expr, ...
```

**Description**

Adds computed columns while keeping existing columns.

**Parameters**

| Parameter | Type | Description |
| --- | --- | --- |
| `alias` | identifier | Name of the new or overwritten column |
| `expr` | expression | Value expression for each row |

**Examples**

```kql
Users | extend doubled = score * 2
Events | extend bucket = bin(ts, 1h), upper_name = toupper(name)
Logs | extend count = toint(extractjson("$.count", payload))
```

**Notes**

- later expressions in the same `extend` can see columns already added earlier in the current result in pandas execution; keep definitions simple for clarity

## `summarize`

**Syntax**

```kql
Table | summarize agg1 = func(...), agg2 = func(...) by expr1, expr2, ...
```

**Description**

Performs aggregation, optionally grouped by one or more expressions.

**Parameters**

| Parameter | Type | Description |
| --- | --- | --- |
| aggregation list | aggregate function calls | Metrics to compute |
| `by` expressions | expressions | Optional grouping keys |

**Examples**

```kql
Users | summarize total=count()
Users | summarize total=count(), avg_score=avg(score) by city
Events | summarize ok_rows=countif(ok), max_value=max(value) by bin(ts, 1h)
```

**Notes**

- aggregate expressions must be function calls
- with no `by` clause, summarize returns a single row even for empty input
- `count()` on empty input returns `0`

## `take` / `limit`

**Syntax**

```kql
Table | take 10
Table | limit 10
```

**Description**

Returns up to the specified number of rows.

**Parameters**

| Parameter | Type | Description |
| --- | --- | --- |
| count | non-negative integer | Maximum number of rows to keep |

**Examples**

```kql
Users | take 5
Users | sort by score desc | limit 3
```

**Notes**

- `take` and `limit` are synonyms
- without an explicit sort, row order depends on the preceding pipeline output order

## `count`

**Syntax**

```kql
Table | count
```

**Description**

Counts the number of rows in the current pipeline input.

**Return shape**

A one-row DataFrame with a `Count` column.

**Examples**

```kql
Users | count
Users | where ok == true | count
```

**Notes**

- unlike `summarize count()`, the column name is capitalized as `Count`
- count on empty input returns `0`

## `sort by` / `order by`

**Syntax**

```kql
Table | sort by expr1 asc, expr2 desc
Table | order by expr1 asc, expr2 desc
```

**Description**

Orders the result using one or more sort keys.

**Parameters**

| Parameter | Type | Description |
| --- | --- | --- |
| expression | expression | Value used for ordering |
| direction | `asc` or `desc` | Optional sort direction; default is ascending |

**Examples**

```kql
Users | sort by score desc
Users | order by city asc, score desc
```

**Notes**

- `sort by` and `order by` are synonyms
- multi-key sorts are stable in the pandas fallback path

## `top`

**Syntax**

```kql
Table | top 5 by score desc
```

**Description**

Sorts by a single key and returns the first `N` rows.

**Parameters**

| Parameter | Type | Description |
| --- | --- | --- |
| count | non-negative integer | Number of rows to return |
| sort key | expression plus direction | Ordering used before limiting |

**Examples**

```kql
Users | top 3 by score desc
Events | top 10 by ts asc
```

**Notes**

- conceptually equivalent to sort plus take, but shorter to write

## `distinct`

**Syntax**

```kql
Table | distinct expr1, expr2, ...
```

**Description**

Removes duplicate rows based on the selected expressions.

**Parameters**

| Parameter | Type | Description |
| --- | --- | --- |
| expressions | expressions | Columns or expressions whose unique combinations should be returned |

**Examples**

```kql
Users | distinct city
Users | distinct name, city
```

**Notes**

- duplicate elimination happens over the selected expression output, not the whole original row

## `parse`

**Syntax**

```kql
Table | parse SourceExpr with "literal" capture * capture ...
```

**Description**

Extracts fields from text using a simple pattern language.

**Parameters**

| Parameter | Type | Description |
| --- | --- | --- |
| `SourceExpr` | expression resolving to text | Source string to parse |
| string literal | literal pattern element | Exact text to match |
| `*` | skip marker | Match but do not capture intermediate text |
| capture name | identifier | Create a new output column with the matched text |

**Examples**

```kql
Logs | parse Message with "user=" user " action=" action
Logs | parse Message with "payload=" payload
Logs | parse Message with "user=" user * "status=" status
```

**Notes**

- `parse` is the main pandas-only operator in the current engine
- output captures are strings
- pattern matching is anchored to the full source text

## Expression-level operators

## Equality and inequality: `==`, `=`, `!=`, `<>`

**Syntax**

```kql
left == right
left = right
left != right
left <> right
```

**Description**

Compares two values for equality or inequality.

**Examples**

```kql
Users | where city == "London"
Users | where score != 0
```

**Notes**

- `==` and `=` behave the same in AdxLite
- `!=` and `<>` behave the same in AdxLite

## Ordering comparisons: `<`, `<=`, `>`, `>=`

**Syntax**

```kql
left < right
left <= right
left > right
left >= right
```

**Description**

Performs standard comparison operations.

**Examples**

```kql
Users | where score >= 10
Events | where ts < datetime(2024-02-01)
```

**Notes**

- datetime comparisons rely on the project's ISO-8601 datetime strategy

## `contains`

**Syntax**

```kql
left contains right
```

**Description**

Checks whether the left string contains the right string as a substring.

**Examples**

```kql
Logs | where Message contains "error"
Users | where city contains "don"
```

**Notes**

- AdxLite implements `contains` as a case-sensitive substring match
- there is no dedicated `!contains` token; use `not (col contains "x")` instead

## `startswith`

**Syntax**

```kql
left startswith right
```

**Description**

Checks whether the left string begins with the right string.

**Examples**

```kql
Users | where name startswith "Ad"
```

**Notes**

- translated through SQLite `LIKE` in the SQL path, so case behavior may depend on SQLite collation details

## `endswith`

**Syntax**

```kql
left endswith right
```

**Description**

Checks whether the left string ends with the right string.

**Examples**

```kql
Users | where email endswith ".com"
```

**Notes**

- translated through SQLite `LIKE` in the SQL path, so case behavior may depend on SQLite collation details

## `has`

**Syntax**

```kql
left has right
```

**Description**

Checks for a case-insensitive whole-token-style match using a word-boundary regex strategy.

**Examples**

```kql
Logs | where Message has "login"
```

**Notes**

- AdxLite's `has` is implemented with a regex word-boundary test
- there is no dedicated `!has` token; use `not (col has "x")` instead

## `in` and `not in`

**Syntax**

```kql
left in (value1, value2, ...)
left not in (value1, value2, ...)
```

**Description**

Checks whether a value is included or excluded from a list.

**Examples**

```kql
Users | where city in ("London", "Paris")
Users | where city not in ("Arlington")
```

**Notes**

- the negated form is written as two tokens: `not in`
- there is no `!in` token in the current parser

## `between` and `not between`

**Syntax**

```kql
left between (lower .. upper)
left not between (lower .. upper)
```

**Description**

Checks whether a value lies within an inclusive range.

**Examples**

```kql
Users | where score between (10 .. 20)
Events | where ts not between (datetime(2024-01-01) .. datetime(2024-01-31))
```

**Notes**

- range endpoints are inclusive
- the negated form is written as `not between`, not `!between`

## `=~`

**Syntax**

```kql
left =~ right
```

**Description**

Performs case-insensitive equality comparison.

**Examples**

```kql
Users | where name =~ "ada"
```

**Notes**

- useful when exact equality is needed but user-entered case may vary

## `!~`

**Syntax**

```kql
left !~ right
```

**Description**

Performs case-insensitive inequality comparison.

**Examples**

```kql
Users | where name !~ "ada"
```

## `matches regex`

**Syntax**

```kql
left matches regex pattern
```

**Description**

Returns true when the regex pattern matches any substring of the left value.

**Examples**

```kql
Logs | where Message matches regex "error|warn"
Logs | where Message matches regex "user=(\w+)"
```

**Notes**

- AdxLite uses partial-match semantics, not full-string-match semantics
- internally backed by a Python regex search helper

## Logical operators: `and`, `or`, `not`

**Syntax**

```kql
expr1 and expr2
expr1 or expr2
not expr
```

**Description**

Combines boolean expressions.

**Examples**

```kql
Users | where score >= 10 and city == "London"
Users | where not (city == "London")
```

**Notes**

- `not` is also the way to express negation for predicates such as `contains` and `has`

## Arithmetic operators: `+`, `-`, `*`, `/`, `%`

**Syntax**

```kql
left + right
left - right
left * right
left / right
left % right
```

**Description**

Performs arithmetic over numeric expressions.

**Examples**

```kql
Users | extend doubled = score * 2
Users | extend ratio = good / total
```

## Related documents

- [KQL syntax](kql-syntax.md)
- [Functions reference](functions.md)
- [Advanced query patterns](../guides/advanced-queries.md)
- [Limitations](limitations.md)
