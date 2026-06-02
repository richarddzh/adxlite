# KQL Syntax Reference

This document specifies the KQL syntax supported by AdxLite. It is a reference for the implemented subset, not a description of the full Azure Data Explorer language.

If you want guided examples, see [Quickstart](../guides/quickstart.md) and [Advanced query patterns](../guides/advanced-queries.md). If you want operator semantics, see [Operators reference](operators.md). If you want function signatures, see [Functions reference](functions.md).

## Scope of this syntax

AdxLite supports a multi-table, pipeline-oriented subset of KQL. The grammar is intentionally smaller than full Kusto, but the supported surface is designed to be readable and useful for local analytics.

Main constructs supported today:

- `let` bindings (scalar values and tabular sub-queries)
- source table references
- `union` (source form and pipe form)
- `join` (all 9 Kusto join kinds with sub-pipelines)
- pipe-delimited tabular operators
- arithmetic, comparison, logical, and function-call expressions
- string, number, boolean, datetime, and timespan literals
- `.append TableName <| query` management command

## High-level grammar overview

The following grammar is descriptive rather than machine-generated, but it closely matches the implemented parser.

```text
statement        := append_command | kql_statement
kql_statement    := let_binding* body
let_binding      := 'let' identifier '=' (expression | pipeline) ';'
body             := append_command | union_source | pipeline
append_command   := '.' 'append' identifier '<|' pipeline
union_source     := 'union' union_params table_list ('|' operator)*
pipeline         := table_ref ('|' operator)*
table_ref        := identifier

union_params     := ('kind' '=' ('inner' | 'outer'))? ('withsource' '=' identifier)?
table_list       := identifier (',' identifier)*

operator         := where_op
                  | project_op
                  | project_away_op
                  | extend_op
                  | summarize_op
                  | take_op
                  | count_op
                  | sort_op
                  | top_op
                  | distinct_op
                  | parse_op
                  | union_op
                  | join_op

union_op         := 'union' union_params table_list
join_op          := 'join' ('kind' '=' join_kind)? '(' pipeline ')' 'on' join_conditions
join_kind        := 'inner' | 'innerunique' | 'leftouter' | 'rightouter'
                  | 'fullouter' | 'leftanti' | 'leftsemi' | 'rightanti' | 'rightsemi'
join_conditions  := join_condition (',' join_condition)*
join_condition   := identifier | '$left' '.' identifier '==' '$right' '.' identifier

where_op         := 'where' expression
project_op       := 'project' named_expr (',' named_expr)*
project_away_op  := ('project-away' | 'project_away') identifier (',' identifier)*
extend_op        := 'extend' named_expr (',' named_expr)*
summarize_op     := 'summarize' named_expr (',' named_expr)* ('by' expression (',' expression)*)?
take_op          := ('take' | 'limit') number
count_op         := 'count'
sort_op          := ('sort' 'by' | 'order' 'by') sort_key (',' sort_key)*
top_op           := 'top' number 'by' sort_key
distinct_op      := 'distinct' expression (',' expression)*
parse_op         := 'parse' primary 'with' parse_pattern
```

## Table reference syntax

A query starts with a source table name.

```kql
Users
Events
[User Events]
```

### Rules

- the source can be a single table name, or a `union` source form
- `let` bindings can precede the pipeline to define reusable names
- `join` sub-pipelines are written as `(TableName | operators...)`
- bracketed identifiers allow spaces or punctuation in names

## Pipe operator syntax

KQL pipelines compose transformations using `|`.

```kql
Users | where score >= 10 | project name, score
```

Each operator consumes the rows produced by the previous stage. This ordered pipeline model is preserved internally with nested SQL subqueries and, when needed, pandas post-processing.

## Named expressions

Several operators accept named expressions.

Syntax:

```text
named_expr := alias '=' expression | expression
```

Examples:

```kql
project name, score
extend doubled = score * 2
summarize total=count(), avg_score=avg(score) by city
```

### Alias inference

If you omit an explicit alias:

- an identifier keeps its own name
- many function calls use the function name as the output column name
- more complex expressions may fall back to a generic inferred name in some internal paths, so explicit aliases are recommended for readability

## Expression grammar overview

Expressions support logical, comparison, arithmetic, function-call, and literal forms.

```text
expression       := or_expr
or_expr          := and_expr ('or' and_expr)*
and_expr         := not_expr ('and' not_expr)*
not_expr         := 'not' not_expr | comparison_expr
comparison_expr  := additive_expr (comparison_tail)*
additive_expr    := multiplicative_expr (('+' | '-') multiplicative_expr)*
multiplicative_expr := unary_expr (('*' | '/' | '%') unary_expr)*
unary_expr       := ('+' | '-') unary_expr | primary
primary          := identifier
                  | literal
                  | function_call
                  | '(' expression ')'
```

## Comparison and predicate forms

AdxLite supports the following comparison-style forms.

```text
left == right
left = right
left != right
left <> right
left < right
left <= right
left > right
left >= right
left contains right
left startswith right
left endswith right
left has right
left matches regex right
left =~ right
left !~ right
left in (expr, expr, ...)
left not in (expr, expr, ...)
left between (lower .. upper)
left not between (lower .. upper)
```

See [Operators reference](operators.md) for semantic notes and caveats.

## Arithmetic syntax

Supported arithmetic operators:

```text
+  -  *  /  %
```

Examples:

```kql
extend total = price * quantity
extend delta = current - previous
extend ratio = part / whole
```

## Function call syntax

Function calls look like regular KQL-style identifiers followed by parentheses.

```text
function_name(arg1, arg2, ...)
```

Examples:

```kql
tolower(name)
sqrt(metric)
extract("user=(\w+)", 1, Message)
bin(ts, 1h)
```

### Aggregate vs scalar functions

Aggregate functions such as `count()` or `sum(value)` are intended for `summarize`. Using them in scalar expression positions is not supported.

## Identifier rules

AdxLite supports plain identifiers and bracketed identifiers.

### Plain identifiers

A plain identifier may contain:

- letters
- digits after the first character
- underscore `_`
- dollar sign `$`
- hyphen `-` in contexts recognized by the tokenizer

Examples:

```kql
Users
user_name
$value
project-away
```

### Bracketed identifiers

Use square brackets when a name contains spaces or characters that would otherwise be awkward to tokenize.

```kql
[User Events]
[display-name]
[Column With Space]
```

### Notes

- bracketed identifiers are returned without the surrounding brackets internally
- keywords may also be used as identifiers in some positions because the parser accepts keyword tokens when an identifier is expected
- keeping identifiers simple and explicit is still the easiest style to maintain

## Literal syntax

### String literals

AdxLite supports single-quoted and double-quoted string literals.

```kql
"Ada"
'London'
```

Escape behavior includes standard sequences such as `
`, ``, `	`, `\`, `"`, and `'`. Unknown escape sequences are preserved so regex patterns like `\w` and `\d` survive tokenization.

### Number literals

Integers and decimals are supported.

```kql
10
3.14
0
-5
```

The parser stores integer-looking values as integer literals and decimal-looking values as floating-point literals.

### Boolean literals

```kql
true
false
```

Boolean keywords are case-insensitive at the language level.

### Timespan literals

A timespan literal is a number followed by a supported unit.

```kql
1d
12h
30m
5s
100ms
1.5h
```

Supported units:

- `d`
- `h`
- `m`
- `s`
- `ms`

### Datetime literals

AdxLite supports `datetime(...)` literal syntax.

Examples:

```kql
datetime(2024-01-02)
datetime(2024-01-02T10:15:00)
datetime("2024-01-02T10:15:00")
```

The parser collects the inner content as a datetime-kind literal. At execution time it is passed as a bound value to SQL or pandas evaluation.

## Parse-pattern syntax

The `parse` operator uses its own mini-pattern language.

```text
parse_pattern := (string_literal | '*' | identifier)+
```

Meaning of each part:

- string literal: exact text to match
- `*`: skip text without capturing it
- identifier: capture text into a new output column

Example:

```kql
parse Message with "user=" user " action=" action
```

## Sort-key syntax

Sort and top operators use sort keys.

```text
sort_key := expression ('asc' | 'desc')?
```

Examples:

```kql
sort by ts desc
sort by city asc, score desc
top 5 by score desc
```

If no direction is supplied, ascending order is assumed.

## Management command syntax

AdxLite supports one management-style command:

```kql
.append Archive <| Events | where ok == true
```

Syntax pieces:

- leading `.` for command mode
- `append` keyword
- target table identifier
- `<|` separator
- a normal query pipeline providing the rows to append

Nested management commands are not supported.

## Case sensitivity rules

Case sensitivity in AdxLite has several layers.

### Keywords

Keywords are parsed case-insensitively.

Examples that parse equivalently:

```kql
WHERE
where
WhErE
```

### Identifiers

Identifiers preserve their written spelling in the AST. SQLite itself is generally forgiving about identifier casing, but it is best to treat table and column names as case-stable for readability and consistency.

### String comparison operators

- `==` and `=` are case-sensitive equality comparisons
- `=~` is case-insensitive equality
- `!~` is case-insensitive inequality
- `contains` is case-sensitive substring search
- `has` is implemented as a case-insensitive whole-token-style match
- `matches regex` depends on the regex pattern you provide and uses Python regex semantics behind the scenes

### Notes on `startswith` and `endswith`

These operators are translated through SQLite `LIKE` in the SQL path. SQLite's exact case behavior for `LIKE` can vary with collation and build configuration, so if you need predictable case handling, normalize with `tolower()` or `toupper()` explicitly.

## Unsupported syntactic categories

The parser deliberately rejects or marks unsupported several major KQL categories, including:

- `mv-expand`
- `mv-apply`
- `render`
- `invoke`
- `evaluate`
- function `let` (lambda definitions with parameters)

The following were previously unsupported but are now implemented:

- `let` (scalar and tabular bindings)
- `union` (source form and pipe form)
- `join` (all 9 Kusto join kinds)

See [Limitations](limitations.md) for the full discussion.

## Worked examples

### Example: simple filter and projection

```kql
Users | where score >= 10 | project name, score
```

### Example: summarize with aliases

```kql
Users | summarize total=count(), avg_score=avg(score) by city
```

### Example: parse and project-away

```kql
Logs | parse Message with "user=" user " action=" action | project-away Message
```

### Example: distinct with bracketed identifiers

```kql
[User Events] | distinct [User Name], [Event Type]
```

## Related documents

- [Operators reference](operators.md)
- [Functions reference](functions.md)
- [Limitations](limitations.md)
- [Architecture](../design/architecture.md)
