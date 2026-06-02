# adxlite

A local SQLite-based database with Kusto Query Language (KQL) support for Python.

## Installation

```bash
pip install adxlite
```

## Quick Start

```python
import pandas as pd
from adxlite import AdxLiteClient

client = AdxLiteClient()  # in-memory, or pass a path for persistence
client.ingest("Users", pd.DataFrame({
    "name": ["Ada", "Alan", "Grace"],
    "city": ["London", "London", "Arlington"],
    "score": [10, 20, 30],
}))

result = client.query('Users | where city == "London" | project name, score')
print(result)
```

## Features

- SQLite-backed persistent storage with KQL query interface
- Hybrid SQL + pandas execution for optimal performance
- Full KQL parser with support for common operators
- Type-aware schema metadata
- Depends on [adxpandas](../adxpandas/) for parser and pandas execution

## Documentation

See the [AdxLite documentation](https://adxlite.github.io/adxlite/) for comprehensive guides.
