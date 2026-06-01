# AdxLite

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-pytest-success)](tests)
[![Docs](https://img.shields.io/badge/docs-complete-blueviolet)](docs/README.md)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

AdxLite is a local, SQLite-backed analytical engine that lets Python applications query pandas-ingested tables with a practical subset of Kusto Query Language (KQL). It is designed for embedded analytics, reproducible local experimentation, and testable data workflows: data is stored in a single SQLite database, KQL pipelines are parsed and translated to SQL, and advanced features such as `parse` are finished with pandas post-processing when SQL alone is not sufficient.

## Why AdxLite exists

Many developers like the expressiveness of KQL, but do not need—or cannot use—a remote Azure Data Explorer cluster for local analysis, CI runs, notebooks, or small application features. AdxLite fills that gap by combining familiar KQL pipeline syntax with a lightweight file database and a pure-Python programming model.

The project is intentionally local-first:

- no external cluster connections
- no service dependency at query time
- no hidden remote state
- no daemon to manage
- no server process beyond SQLite embedded in the Python runtime

## Feature highlights

AdxLite focuses on a coherent, well-documented subset of KQL rather than trying to clone the entire Kusto surface area.

### Storage and ingestion

- SQLite-backed local database files or `:memory:` databases
- DataFrame ingestion through `AdxLiteClient.ingest()` and `ingest_from_pandas()`
- `replace` mode for full-table reloads
- `append` mode for incremental ingestion into an existing schema
- schema metadata stored alongside the SQLite data
- datetime column round-tripping through ISO-8601 storage plus metadata restoration

### Query model

- KQL-style pipe composition: `Table | where ... | summarize ...`
- nested-subquery SQL generation for pipeline correctness
- parameterized SQL for user literals
- pandas DataFrame results for every query
- hybrid execution path for `parse`
- `.append TableName <| query` management command for local data movement

### Supported tabular operators

- `where`
- `project`
- `project-away`
- `extend`
- `summarize`
- `take` / `limit`
- `count`
- `sort by` / `order by`
- `top`
- `distinct`
- `parse`

### Supported scalar and aggregate capabilities

- string predicates such as `contains`, `startswith`, `endswith`, `has`, `in`, `between`, `=~`, `!~`, and `matches regex`
- aggregate functions such as `count`, `sum`, `avg`, `min`, `max`, `dcount`, `countif`, `sumif`, and `avgif`
- string helpers such as `tolower`, `toupper`, `substring`, `strcat`, `replace_string`, `reverse`, `countof`, `indexof`, `split`, and `extract`
- math helpers such as `log`, `log2`, `log10`, `pow`, `sqrt`, `exp`, `ceiling`, `floor`, `sign`, `pi`, `round`, and `abs`
- datetime helpers such as `now`, `ago`, `bin`, `datetime_diff`, `format_datetime`, and `datetime_add`
- JSON helpers such as `parse_json`, `dynamic`, and `extractjson`
- conditional and conversion helpers such as `iif`, `iff`, `coalesce`, `isnull`, `isempty`, `tostring`, `toint`, and `todouble`

## Installation

Install the package into a virtual environment for normal usage:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install adxlite
```

For local development in this repository:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

## Quick example

```python
import pandas as pd
from adxlite import AdxLiteClient

df = pd.DataFrame(
    {
        "user": ["ada", "alan", "grace", "ada"],
        "city": ["London", "London", "Arlington", "London"],
        "value": [10, 20, 30, 40],
        "ts": pd.to_datetime([
            "2024-01-01T10:05:00",
            "2024-01-01T10:45:00",
            "2024-01-02T08:00:00",
            "2024-01-02T08:30:00",
        ]),
    }
)

with AdxLiteClient("analytics.db") as client:
    client.ingest("Events", df)

    result = client.query(
        """
        Events
        | where city == "London"
        | extend hour_bucket = bin(ts, 1h), upper_user = toupper(user)
        | summarize total=count(), max_value=max(value) by hour_bucket, upper_user
        | sort by hour_bucket asc, upper_user asc
        """
    )

    print(result)
```

Example output:

```text
           hour_bucket upper_user  total  max_value
0  2024-01-01T10:00:00        ADA      1         10
1  2024-01-01T10:00:00       ALAN      1         20
2  2024-01-02T08:00:00        ADA      1         40
```

## Supported KQL subset at a glance

AdxLite is intentionally narrower than Azure Data Explorer. The project supports the subset that maps cleanly to SQLite and pandas while keeping predictable semantics.

| Area | Supported |
| --- | --- |
| Data source | Local SQLite tables created from pandas DataFrames |
| Query shape | Single-table KQL pipelines |
| Table mutation | `.append TableName <| query` |
| Datetime literals | `datetime(2024-01-02)` |
| Timespans | `1d`, `12h`, `30m`, `5s`, `100ms` |
| Result type | `pandas.DataFrame` |
| Advanced parsing | `parse` with pandas post-processing |

Unsupported categories include `join`, `union`, `mv-expand`, `mv-apply`, `render`, `let`, `invoke`, and `evaluate`. See [docs/reference/limitations.md](docs/reference/limitations.md) for details and workarounds.

## Documentation map

Start here if you are new to the project:

- [Documentation index](docs/README.md)
- [Quickstart guide](docs/guides/quickstart.md)
- [Ingestion guide](docs/guides/ingestion.md)
- [Advanced query patterns](docs/guides/advanced-queries.md)

Read these if you want internals or exact semantics:

- [Architecture](docs/design/architecture.md)
- [Design decisions](docs/design/decisions.md)
- [Type system](docs/design/type-system.md)
- [Requirements](docs/design/requirements.md)
- [KQL syntax reference](docs/reference/kql-syntax.md)
- [Functions reference](docs/reference/functions.md)
- [Operators reference](docs/reference/operators.md)
- [API reference](docs/reference/api.md)
- [Limitations](docs/reference/limitations.md)

## Development setup

Clone the repository and install editable dependencies:

```bash
git clone <your-fork-or-repository-url>
cd adxlite
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .[dev]
```

Run the test suite:

```bash
python -m pytest -q
```

The test suite covers parser behavior, translation, UDF semantics, datetime handling, advanced query behavior, and end-to-end execution.

## Project structure

```text
src/adxlite/
├── client.py           # Public Python API
├── exceptions.py       # Public exception types
├── parser/             # Tokenizer, AST, parser
├── translator/         # KQL-to-SQL translation
├── storage/            # SQLite storage and UDF registration
└── engine/             # Planning, execution, pandas fallback
```

## Typical use cases

- local analytics in unit and integration tests
- notebook exploration without standing up an external service
- deterministic fixtures backed by a single database file
- embedded application features that need lightweight ad hoc querying
- prototyping KQL-like workflows before moving to a larger execution environment

## What AdxLite is not

AdxLite is not a remote query client, a distributed execution engine, or a full Azure Data Explorer replacement. It does not connect to external Kusto clusters, does not support multi-database joins, and does not try to reproduce every KQL operator.

## License

This project is licensed under the MIT License. See the repository license file for the exact terms.
