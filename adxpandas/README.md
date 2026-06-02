# adxpandas

Execute Kusto Query Language (KQL) queries directly over one or more pandas DataFrames — no database required.

## Installation

```bash
pip install adxpandas
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

## Features

- Pure pandas execution — no SQLite or other database dependencies
- Full KQL parser with support for common operators
- Operators: where, project, project-away, extend, summarize, sort, top, take, distinct, count, parse, join, union
- Scalar functions: string, math, datetime operations
- Aggregate functions: count, sum, avg, min, max, dcount, countif, sumif, avgif
- let statements (scalar and tabular)
- Union source form queries

## Documentation

See the [AdxLite documentation](https://adxlite.github.io/adxlite/) for comprehensive guides covering both adxlite and adxpandas.
