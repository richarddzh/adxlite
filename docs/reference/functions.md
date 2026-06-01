# Functions Reference

This document lists every scalar and aggregate function currently implemented by AdxLite. Each entry includes the function signature, a short description, parameter table, return type, example, and notes.

For operator syntax such as `matches regex` or `between`, see [Operators reference](operators.md). For data type behavior, see [Type system](../design/type-system.md).

## Function categories

- **Aggregation functions**: Aggregation functions are intended for `summarize` clauses. They consume the current group and return one value per group.
- **String and encoding functions**: These functions operate on text values. Unless stated otherwise, results are strings or integer/string-derived values.
- **Math functions**: Math helpers are available in scalar expressions such as `extend`, `project`, and predicates.
- **Datetime functions**: Datetime helpers operate on ISO-8601 text and datetime-typed columns using the project's local datetime semantics.
- **Regex and JSON functions**: These functions support partial regex search, capture extraction, and JSON-text workflows.
- **Conditional and conversion functions**: These functions help with branching, null handling, and type conversion.

## General notes

- Function names are parsed case-insensitively.
- Aggregate functions are intended for `summarize` and are not valid in general scalar positions.
- Many functions return `null`/missing values when required inputs are null.
- JSON-oriented helpers return JSON text or string values rather than nested dynamic objects.
- When exact semantics differ from Azure Data Explorer, the notes call that out or point to [Limitations](limitations.md).

## Aggregation functions

Aggregation functions are intended for `summarize` clauses. They consume the current group and return one value per group.

### `count`

**Signature**

```kql
count()
```

**Description**

Counts input rows in the current group or entire input when no grouping key is present.

**Parameters**

This function takes no parameters.

**Return type**

long

**Example**

```kql
Events | summarize total=count() by city
```

**Notes**

- Use inside `summarize`.
- On empty input without grouping, returns `0`.

### `sum`

**Signature**

```kql
sum(expr)
```

**Description**

Sums numeric values.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `expr` | numeric expression | Value to sum |

**Return type**

same logical numeric family as input, commonly real or long

**Example**

```kql
Events | summarize total_value=sum(value)
```

**Notes**

- Nulls are ignored according to underlying aggregation behavior.

### `avg`

**Signature**

```kql
avg(expr)
```

**Description**

Computes the arithmetic mean of numeric values.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `expr` | numeric expression | Value to average |

**Return type**

real

**Example**

```kql
Events | summarize avg_value=avg(value) by city
```

**Notes**

- Typically returns floating-point output.

### `min`

**Signature**

```kql
min(expr)
```

**Description**

Returns the minimum value in each group.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `expr` | scalar expression | Value to compare |

**Return type**

same logical type as the input expression when inferable

**Example**

```kql
Events | summarize first_seen=min(ts)
```

**Notes**

- Works for numbers, strings, and datetimes using the engine's current comparison semantics.

### `max`

**Signature**

```kql
max(expr)
```

**Description**

Returns the maximum value in each group.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `expr` | scalar expression | Value to compare |

**Return type**

same logical type as the input expression when inferable

**Example**

```kql
Events | summarize max_value=max(value)
```

**Notes**

- Useful for latest timestamp or highest score style queries.

### `dcount`

**Signature**

```kql
dcount(expr)
```

**Description**

Counts distinct non-null values.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `expr` | scalar expression | Value whose distinct count should be computed |

**Return type**

long

**Example**

```kql
Events | summarize unique_users=dcount(user)
```

**Notes**

- Implemented as exact distinct count, not approximate HyperLogLog-style behavior.

### `countif`

**Signature**

```kql
countif(predicate)
```

**Description**

Counts rows for which the predicate is true.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `predicate` | bool expression | Condition to test per row |

**Return type**

long

**Example**

```kql
Events | summarize ok_rows=countif(ok)
```

**Notes**

- Equivalent to summing a boolean predicate over the group.

### `sumif`

**Signature**

```kql
sumif(expr, predicate)
```

**Description**

Sums values only for rows matching the predicate.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `expr` | numeric expression | Value to sum |
| `predicate` | bool expression | Condition selecting rows to include |

**Return type**

same logical numeric family as input, commonly real or long

**Example**

```kql
Events | summarize ok_value=sumif(value, ok)
```

**Notes**

- Rows failing the predicate do not contribute to the sum.

### `avgif`

**Signature**

```kql
avgif(expr, predicate)
```

**Description**

Averages values only for rows matching the predicate.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `expr` | numeric expression | Value to average |
| `predicate` | bool expression | Condition selecting rows to include |

**Return type**

real

**Example**

```kql
Events | summarize ok_avg=avgif(value, ok)
```

**Notes**

- Useful for conditional metrics without pre-filtering the whole dataset.

## String and encoding functions

These functions operate on text values. Unless stated otherwise, results are strings or integer/string-derived values.

### `tolower`

**Signature**

```kql
tolower(text)
```

**Description**

Converts text to lowercase.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string | Input text |

**Return type**

string

**Example**

```kql
Users | extend name_lower=tolower(name)
```

**Notes**

- Useful for explicit case normalization before comparisons.

### `toupper`

**Signature**

```kql
toupper(text)
```

**Description**

Converts text to uppercase.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string | Input text |

**Return type**

string

**Example**

```kql
Users | extend name_upper=toupper(name)
```

**Notes**

- Useful for display or normalization.

### `strlen`

**Signature**

```kql
strlen(text)
```

**Description**

Returns string length.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string | Input text |

**Return type**

long

**Example**

```kql
Users | extend name_len=strlen(name)
```

**Notes**

- Counts characters according to the underlying engine string semantics.

### `trim`

**Signature**

```kql
trim(text) or trim(chars, text)
```

**Description**

Trims whitespace or a specified set of characters from both ends of a string.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string | Input text when using one argument |
| `chars` | string | Characters to trim when using the two-argument form |

**Return type**

string

**Example**

```kql
Users | extend clean=trim(name)
```

**Notes**

- In the two-argument form, the first argument is the trim character set and the second is the text value.

### `substring`

**Signature**

```kql
substring(text, start[, length])
```

**Description**

Returns a substring using 0-based indexing.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string | Input text |
| `start` | long | 0-based start position |
| `length` | long | Optional length |

**Return type**

string

**Example**

```kql
Users | extend prefix=substring(name, 0, 3)
```

**Notes**

- The start index is 0-based in AdxLite.

### `strcat`

**Signature**

```kql
strcat(arg1, arg2, ...)
```

**Description**

Concatenates one or more values as text.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `arg1..n` | scalar | Values to concatenate in order |

**Return type**

string

**Example**

```kql
Users | extend key=strcat(name, ':', city)
```

**Notes**

- At least one argument is required.

### `replace_string`

**Signature**

```kql
replace_string(text, old, new)
```

**Description**

Replaces all occurrences of one substring with another.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string | Input text |
| `old` | string | Substring to replace |
| `new` | string | Replacement text |

**Return type**

string

**Example**

```kql
Logs | extend clean=replace_string(Message, 'error', 'ERR')
```

**Notes**

- Replacement is literal string replacement, not regex replacement.

### `reverse`

**Signature**

```kql
reverse(text)
```

**Description**

Reverses the characters in a string.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string | Input text |

**Return type**

string

**Example**

```kql
Users | extend reversed=reverse(name)
```

**Notes**

- Null input returns null.

### `countof`

**Signature**

```kql
countof(text, needle)
```

**Description**

Counts occurrences of a substring.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string | Input text |
| `needle` | string | Substring to count |

**Return type**

long

**Example**

```kql
Logs | extend equals=countof(Message, '=')
```

**Notes**

- Uses non-overlapping substring counting semantics.

### `indexof`

**Signature**

```kql
indexof(text, needle)
```

**Description**

Returns the 0-based position of the first substring occurrence.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string | Input text |
| `needle` | string | Substring to locate |

**Return type**

long

**Example**

```kql
Logs | extend pos=indexof(Message, 'user=')
```

**Notes**

- Returns `-1` when the substring is not found.

### `split`

**Signature**

```kql
split(text, delimiter)
```

**Description**

Splits text by a delimiter and returns a JSON array string.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string | Input text |
| `delimiter` | string | Separator |

**Return type**

string (JSON array text)

**Example**

```kql
Users | extend parts=split(email, '@')
```

**Notes**

- The result is JSON text such as `["a", "b"]`, not a native array column.

### `url_encode`

**Signature**

```kql
url_encode(text)
```

**Description**

Percent-encodes text for URL usage.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string | Input text |

**Return type**

string

**Example**

```kql
Users | extend encoded=url_encode(name)
```

**Notes**

- Backed by Python URL quoting logic.

### `url_decode`

**Signature**

```kql
url_decode(text)
```

**Description**

Decodes percent-encoded URL text.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string | Input text |

**Return type**

string

**Example**

```kql
Users | extend decoded=url_decode(encoded)
```

**Notes**

- Useful when ingesting URL-escaped payloads.

### `base64_encode_tostring`

**Signature**

```kql
base64_encode_tostring(text)
```

**Description**

Encodes text as Base64.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string | Input text |

**Return type**

string

**Example**

```kql
Users | extend token=base64_encode_tostring(name)
```

**Notes**

- Output is ASCII Base64 text.

### `base64_decode_tostring`

**Signature**

```kql
base64_decode_tostring(text)
```

**Description**

Decodes Base64 text into a string.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string | Base64 input |

**Return type**

string

**Example**

```kql
Users | extend name_plain=base64_decode_tostring(token)
```

**Notes**

- Invalid Base64 raises an execution-time failure in the underlying Python helper.

## Math functions

Math helpers are available in scalar expressions such as `extend`, `project`, and predicates.

### `log`

**Signature**

```kql
log(value)
```

**Description**

Computes the natural logarithm.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | numeric | Input value |

**Return type**

real

**Example**

```kql
Metrics | extend ln_value=log(metric)
```

**Notes**

- Null input returns null.

### `log2`

**Signature**

```kql
log2(value)
```

**Description**

Computes the base-2 logarithm.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | numeric | Input value |

**Return type**

real

**Example**

```kql
Metrics | extend lg=log2(metric)
```

**Notes**

- Useful for power-of-two style metrics.

### `log10`

**Signature**

```kql
log10(value)
```

**Description**

Computes the base-10 logarithm.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | numeric | Input value |

**Return type**

real

**Example**

```kql
Metrics | extend lg10=log10(metric)
```

**Notes**

- Used in the test suite for numeric validation.

### `pow`

**Signature**

```kql
pow(left, right)
```

**Description**

Raises the first value to the power of the second.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `left` | numeric | Base |
| `right` | numeric | Exponent |

**Return type**

real

**Example**

```kql
Metrics | extend squared=pow(metric, 2)
```

**Notes**

- Returns floating-point output.

### `sqrt`

**Signature**

```kql
sqrt(value)
```

**Description**

Computes the square root.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | numeric | Input value |

**Return type**

real

**Example**

```kql
Metrics | extend root=sqrt(metric)
```

**Notes**

- Used in integration tests with floating-point comparisons.

### `exp`

**Signature**

```kql
exp(value)
```

**Description**

Computes e raised to the given value.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | numeric | Exponent |

**Return type**

real

**Example**

```kql
Metrics | extend exp_value=exp(metric)
```

**Notes**

- Backed by Python math semantics in the UDF layer.

### `ceiling`

**Signature**

```kql
ceiling(value)
```

**Description**

Rounds a numeric value upward to the nearest integer.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | numeric | Input value |

**Return type**

long

**Example**

```kql
Metrics | extend up=ceiling(metric)
```

**Notes**

- Returns integer-like output.

### `floor`

**Signature**

```kql
floor(value)
```

**Description**

Rounds a numeric value downward to the nearest integer.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | numeric | Input value |

**Return type**

long

**Example**

```kql
Metrics | extend down=floor(metric)
```

**Notes**

- Returns integer-like output.

### `sign`

**Signature**

```kql
sign(value)
```

**Description**

Returns `-1`, `0`, or `1` depending on the sign of the input.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | numeric | Input value |

**Return type**

long

**Example**

```kql
Metrics | extend s=sign(delta)
```

**Notes**

- Negative values map to `-1`, positive values to `1`, and zero to `0`.

### `pi`

**Signature**

```kql
pi()
```

**Description**

Returns the mathematical constant π.

**Parameters**

This function takes no parameters.

**Return type**

real

**Example**

```kql
Metrics | extend circumference=2 * pi() * radius
```

**Notes**

- Takes no arguments.

### `round`

**Signature**

```kql
round(value[, digits])
```

**Description**

Rounds a numeric value, optionally to a specified number of digits.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | numeric | Input value |
| `digits` | long | Optional number of digits |

**Return type**

real

**Example**

```kql
Metrics | extend rounded=round(metric, 2)
```

**Notes**

- When `digits` is omitted, rounds to the nearest integer-style value.

### `abs`

**Signature**

```kql
abs(value)
```

**Description**

Returns absolute value.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | numeric | Input value |

**Return type**

real or long depending on input

**Example**

```kql
Metrics | extend magnitude=abs(delta)
```

**Notes**

- Useful when analyzing signed differences.

## Datetime functions

Datetime helpers operate on ISO-8601 text and datetime-typed columns using the project's local datetime semantics.

### `now`

**Signature**

```kql
now()
```

**Description**

Returns the current UTC timestamp as an ISO-8601 string value.

**Parameters**

This function takes no parameters.

**Return type**

datetime-like string

**Example**

```kql
Events | extend query_time=now()
```

**Notes**

- Current implementation uses UTC and emits ISO text.

### `ago`

**Signature**

```kql
ago(timespan)
```

**Description**

Subtracts a timespan from the current UTC time.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `timespan` | timespan literal | Duration such as `1d` or `30m` |

**Return type**

datetime-like string

**Example**

```kql
Events | where ts >= ago(1d)
```

**Notes**

- Supported timespan units are `d`, `h`, `m`, `s`, and `ms`.

### `bin`

**Signature**

```kql
bin(value, timespan)
```

**Description**

Rounds a datetime value down to the nearest bucket boundary.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | datetime-like | Input timestamp |
| `timespan` | timespan literal | Bucket width |

**Return type**

datetime-like string

**Example**

```kql
Events | extend bucket=bin(ts, 1h)
```

**Notes**

- Commonly used before `summarize` for time bucketing.

### `datetime_diff`

**Signature**

```kql
datetime_diff(unit, left, right)
```

**Description**

Returns the difference between two datetimes in the requested unit.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `unit` | string | `day`, `hour`, `minute`, `second`, or `millisecond` |
| `left` | datetime-like | Left timestamp |
| `right` | datetime-like | Right timestamp |

**Return type**

long

**Example**

```kql
Events | extend hours=datetime_diff('hour', now(), ts)
```

**Notes**

- The result can be negative when `left` is earlier than `right`.

### `format_datetime`

**Signature**

```kql
format_datetime(value, format)
```

**Description**

Formats a datetime value as text.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | datetime-like | Input timestamp |
| `format` | string | Format string using tokens such as `yyyy`, `MM`, `dd`, `HH`, `mm`, `ss` |

**Return type**

string

**Example**

```kql
Events | extend day=format_datetime(ts, 'yyyy-MM-dd')
```

**Notes**

- Supported format tokens are a small documented subset, not the full Kusto formatter.

### `datetime_add`

**Signature**

```kql
datetime_add(timespan, value)
```

**Description**

Adds a timespan to a datetime value.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `timespan` | timespan literal | Duration to add |
| `value` | datetime-like | Input timestamp |

**Return type**

datetime-like string

**Example**

```kql
Events | extend next_time=datetime_add(30m, ts)
```

**Notes**

- AdxLite uses a simplified two-argument signature.

## Regex and JSON functions

These functions support partial regex search, capture extraction, and JSON-text workflows.

### `extract`

**Signature**

```kql
extract(pattern, group, text)
```

**Description**

Extracts a regex capture group from text.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `pattern` | string | Regex pattern |
| `group` | long | Capture group index |
| `text` | string | Input text |

**Return type**

string or null

**Example**

```kql
Logs | extend user=extract('user=(\\w+)', 1, Message)
```

**Notes**

- Uses Python regex search semantics and returns the chosen subgroup.

### `parse_json`

**Signature**

```kql
parse_json(text)
```

**Description**

Parses JSON-like input and returns normalized JSON text.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string or JSON-like value | JSON input |

**Return type**

string (JSON text)

**Example**

```kql
Logs | extend payload_json=parse_json(payload)
```

**Notes**

- The result is JSON text, not a nested Python object in the DataFrame.

### `dynamic`

**Signature**

```kql
dynamic(text)
```

**Description**

Alias for `parse_json(text)` in the current implementation.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `text` | string or JSON-like value | JSON input |

**Return type**

string (JSON text)

**Example**

```kql
Logs | extend payload_json=dynamic(payload)
```

**Notes**

- Use when you want Kusto-style dynamic naming but AdxLite still returns JSON text.

### `extractjson`

**Signature**

```kql
extractjson(path, json_text)
```

**Description**

Extracts a value from JSON text using a simple JSONPath-like selector.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `path` | string | Path such as `$.count` or `$.items[0]` |
| `json_text` | string | JSON input text |

**Return type**

string or JSON text or null

**Example**

```kql
Logs | extend count=extractjson('$.count', payload)
```

**Notes**

- Scalar outputs are returned as strings; arrays and objects are returned as JSON text.

## Conditional and conversion functions

These functions help with branching, null handling, and type conversion.

### `iif`

**Signature**

```kql
iif(predicate, then_value, else_value)
```

**Description**

Returns one of two values depending on a predicate.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `predicate` | bool expression | Condition |
| `then_value` | scalar | Value returned when predicate is true |
| `else_value` | scalar | Value returned when predicate is false |

**Return type**

same general type family as branch expressions

**Example**

```kql
Events | extend band=iif(value >= 20, 'high', 'low')
```

**Notes**

- `iff()` is an exact alias.

### `iff`

**Signature**

```kql
iff(predicate, then_value, else_value)
```

**Description**

Alias for `iif(predicate, then_value, else_value)`.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `predicate` | bool expression | Condition |
| `then_value` | scalar | True branch |
| `else_value` | scalar | False branch |

**Return type**

same general type family as branch expressions

**Example**

```kql
Events | extend band=iff(ok, 'ok', 'bad')
```

**Notes**

- Included for Kusto familiarity.

### `coalesce`

**Signature**

```kql
coalesce(arg1, arg2, ...)
```

**Description**

Returns the first non-null value from the argument list.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `arg1..n` | scalar | Candidate values evaluated left to right |

**Return type**

type of the first non-null branch at runtime

**Example**

```kql
Users | extend display=coalesce(nickname, name, 'unknown')
```

**Notes**

- At least one argument is required.

### `isnull`

**Signature**

```kql
isnull(value)
```

**Description**

Checks whether a value is null.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | scalar | Value to test |

**Return type**

bool

**Example**

```kql
Users | where isnull(email)
```

**Notes**

- Useful for nullable or partially populated datasets.

### `isnotnull`

**Signature**

```kql
isnotnull(value)
```

**Description**

Checks whether a value is not null.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | scalar | Value to test |

**Return type**

bool

**Example**

```kql
Users | where isnotnull(email)
```

**Notes**

- Negated counterpart to `isnull()`.

### `isempty`

**Signature**

```kql
isempty(value)
```

**Description**

Checks whether a value is null or the empty string.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | scalar | Value to test |

**Return type**

bool

**Example**

```kql
Users | where isempty(nickname)
```

**Notes**

- Treats null and empty text as empty.

### `isnotempty`

**Signature**

```kql
isnotempty(value)
```

**Description**

Checks whether a value is neither null nor the empty string.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | scalar | Value to test |

**Return type**

bool

**Example**

```kql
Users | where isnotempty(email)
```

**Notes**

- Useful before string operations on optional fields.

### `tostring`

**Signature**

```kql
tostring(value)
```

**Description**

Casts a value to text.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | scalar | Value to convert |

**Return type**

string

**Example**

```kql
Events | extend value_text=tostring(value)
```

**Notes**

- Helpful before concatenation or display formatting.

### `toint`

**Signature**

```kql
toint(value)
```

**Description**

Converts a value to an integer-like representation.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | scalar | Value to convert |

**Return type**

long

**Example**

```kql
Logs | extend count=toint(extractjson('$.count', payload))
```

**Notes**

- Prefer clean numeric input for predictable results across SQL and pandas paths.

### `tolong`

**Signature**

```kql
tolong(value)
```

**Description**

Converts a value to a long integer representation.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | scalar | Value to convert |

**Return type**

long

**Example**

```kql
Logs | extend id_long=tolong(id_text)
```

**Notes**

- Implemented with the same underlying cast behavior as `toint()`.

### `todouble`

**Signature**

```kql
todouble(value)
```

**Description**

Converts a value to floating-point.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | scalar | Value to convert |

**Return type**

real

**Example**

```kql
Logs | extend ratio=todouble(ratio_text)
```

**Notes**

- Use when numeric text should participate in arithmetic.

### `toreal`

**Signature**

```kql
toreal(value)
```

**Description**

Alias for `todouble(value)`.

**Parameters**

| Name | Type | Description |
| --- | --- | --- |
| `value` | scalar | Value to convert |

**Return type**

real

**Example**

```kql
Logs | extend metric=toreal(metric_text)
```

**Notes**

- Included for Kusto naming familiarity.

## Related documents

- [Operators reference](operators.md)
- [KQL syntax](kql-syntax.md)
- [Type system](../design/type-system.md)
- [Advanced query patterns](../guides/advanced-queries.md)
