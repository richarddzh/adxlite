from __future__ import annotations

import math

import pandas as pd

from adxlite import AdxLiteClient


def test_parse_regex_math_and_json_queries() -> None:
    client = AdxLiteClient()
    client.ingest(
        "Logs",
        pd.DataFrame(
            {
                "Message": [
                    "user=ada action=login payload={\"count\": 9}",
                    "user=alan action=logout payload={\"count\": 16}",
                ],
                "metric": [100.0, 1000.0],
            }
        ),
    )
    result = client.query(
        'Logs | parse Message with "user=" user " action=" action " payload=" payload | where Message matches regex "login|logout" | extend root = sqrt(metric), count = extractjson("$.count", payload) | project user, action, root, count | sort by user asc'
    )
    assert result.to_dict(orient="records") == [
        {"user": "ada", "action": "login", "root": 10.0, "count": "9"},
        {"user": "alan", "action": "logout", "root": math.sqrt(1000.0), "count": "16"},
    ]


def test_empty_table_aggregation_semantics() -> None:
    client = AdxLiteClient()
    client.ingest("Empty", pd.DataFrame({"value": pd.Series(dtype="float64")}))
    result = client.query("Empty | summarize total=count(), sum_value=sum(value), avg_value=avg(value), min_value=min(value), max_value=max(value)")
    row = result.iloc[0]
    assert row["total"] == 0
    assert pd.isna(row["sum_value"])
    assert pd.isna(row["avg_value"])
    assert pd.isna(row["min_value"])
    assert pd.isna(row["max_value"])


def test_large_data_query() -> None:
    client = AdxLiteClient()
    frame = pd.DataFrame({"value": list(range(10000)), "group": ["even" if i % 2 == 0 else "odd" for i in range(10000)]})
    client.ingest("Numbers", frame)
    result = client.query("Numbers | where value >= 5000 | summarize total=count(), max_value=max(value) by group | sort by group asc")
    assert result.to_dict(orient="records") == [
        {"group": "even", "total": 2500, "max_value": 9998},
        {"group": "odd", "total": 2500, "max_value": 9999},
    ]
