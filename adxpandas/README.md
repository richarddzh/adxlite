# adxpandas

[![PyPI](https://img.shields.io/pypi/v/adxpandas)](https://pypi.org/project/adxpandas/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://pypi.org/project/adxpandas/)

Execute Kusto Query Language (KQL) queries directly over one or more pandas DataFrames — no database required.

## Installation

```bash
pip install adxpandas
```

For Jupyter notebook support (magic commands and chart rendering):

```bash
pip install adxpandas[notebook]
```

## Quick Start

```python
import pandas as pd
from adxpandas import AdxPandasClient

df = pd.DataFrame({
    "name": ["Ada", "Alan", "Grace"],
    "city": ["London", "London", "Arlington"],
    "score": [10, 20, 30],
})

client = AdxPandasClient({"Users": df})
result = client.query('Users | where city == "London" | project name, score')
print(result)
```

## Wrap: Quick Single-DataFrame Queries

```python
from adxpandas import Wrap

w = Wrap(df)
result = w.execute('self | where city == "London" | project name, score')
print(result.df)

# Method chaining
w.where('city == "London"').project("name", "score").take(5).df
```

## Jupyter Magic

```python
import adxpandas.magic  # registers %kql magic

# Line magic
%kql df | where city == "London" | take 5

# Cell magic
%%kql
df
| where score > 10
| summarize count() by city
```

## Render Charts

```python
w = Wrap(df)
w.execute('self | summarize avg(score) by city | render barchart')
```

## Features

- Pure pandas execution — no SQLite or other database dependencies
- Full KQL parser with support for common operators
- Operators: where, project, project-away, extend, summarize, sort, top, take, distinct, count, parse, join, union, render
- Wrap class for quick single-DataFrame queries with method chaining
- Jupyter `%kql` / `%%kql` magic for interactive notebooks
- Chart rendering: timechart, barchart, columnchart, piechart, linechart
- Scalar functions: string, math, datetime operations
- Aggregate functions: count, sum, avg, min, max, dcount, countif, sumif, avgif
- let statements (scalar and tabular)
- Union source form queries

## Documentation

See the [full documentation](https://richarddzh.github.io/adxlite/) for comprehensive guides covering both adxlite and adxpandas.

## Acknowledgments

Some functionality in adxpandas was inspired by and references [KustoPandas](https://github.com/js850/KustoPandas). We thank the KustoPandas authors for their pioneering work on KQL-over-pandas execution.

## Links

- [GitHub Repository](https://github.com/richarddzh/adxlite)
- [Documentation](https://richarddzh.github.io/adxlite/)
- [Issue Tracker](https://github.com/richarddzh/adxlite/issues)

## License

This project is licensed under the MIT License. See the [LICENSE](../LICENSE) file for details.
