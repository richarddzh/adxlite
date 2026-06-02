from __future__ import annotations

import pandas as pd

from adxpandas import AdxPandasClient


SIZE = 12_000
SALES = pd.DataFrame({
    "id": list(range(SIZE)),
    "kind": ["even" if i % 2 == 0 else "odd" for i in range(SIZE)],
    "value": [i % 100 for i in range(SIZE)],
    "text": [f"item-{i % 250}" for i in range(SIZE)],
    "stamp": pd.date_range("2024-01-01", periods=SIZE, freq="min"),
})
EVENTS = pd.DataFrame({
    "id": list(range(0, SIZE, 3)),
    "flag": ["match" if (i // 3) % 2 == 0 else "hold" for i in range(0, SIZE, 3)],
})
LOGS = pd.DataFrame({
    "Message": [f"user=u{i % 5} action=a{i % 3} code={100 + (i % 7)}" for i in range(SIZE)]
})


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "Sales": SALES,
        "Events": EVENTS,
        "Logs": LOGS,
        "PartA": SALES.iloc[: SIZE // 2][["id", "value"]].copy(),
        "PartB": SALES.iloc[SIZE // 2 :][["id", "value"]].copy(),
    })


def test_count_scales_to_large_inputs() -> None:
    result = _client().query("Sales | count")
    assert result.iloc[0]["Count"] == SIZE


def test_long_pipeline_with_where_extend_and_summarize_handles_large_inputs() -> None:
    result = _client().query(
        "Sales | where value >= 90 | extend doubled = value * 2, tag = strcat(text, '-x') | summarize total=count(), max_double=max(doubled) by kind | sort by kind asc"
    )
    assert result.to_dict(orient='records') == [
        {"kind": "even", "total": 600, "max_double": 196},
        {"kind": "odd", "total": 600, "max_double": 198},
    ]


def test_distinct_followed_by_count_handles_many_duplicates() -> None:
    result = _client().query("Sales | distinct text | count")
    assert result.iloc[0]["Count"] == 250


def test_large_inner_joins_return_the_expected_row_count() -> None:
    result = _client().query("Sales | join kind=inner (Events) on id | count")
    assert result.iloc[0]["Count"] == 4000


def test_large_joins_can_be_grouped_afterward() -> None:
    result = _client().query("Sales | join kind=inner (Events) on id | summarize total=count() by flag | sort by flag asc")
    assert result.to_dict(orient='records') == [
        {"flag": "hold", "total": 2000},
        {"flag": "match", "total": 2000},
    ]


def test_large_unions_preserve_all_rows() -> None:
    result = _client().query("union PartA, PartB | count")
    assert result.iloc[0]["Count"] == SIZE


def test_parse_handles_large_log_tables() -> None:
    result = _client().query(
        'Logs | parse Message with "user=" user " action=" action " code=" code | summarize total=count() by user | sort by user asc'
    )
    assert result.to_dict(orient='records') == [
        {"user": "u0", "total": 2400},
        {"user": "u1", "total": 2400},
        {"user": "u2", "total": 2400},
        {"user": "u3", "total": 2400},
        {"user": "u4", "total": 2400},
    ]


def test_datetime_binning_handles_large_tables() -> None:
    result = _client().query(
        "Sales | where id < 180 | extend bucket = bin(stamp, 1h) | summarize total=count(), max_value=max(value) by bucket | sort by bucket asc"
    )
    assert result.to_dict(orient='records') == [
        {"bucket": "2024-01-01T00:00:00", "total": 60, "max_value": 59},
        {"bucket": "2024-01-01T01:00:00", "total": 60, "max_value": 99},
        {"bucket": "2024-01-01T02:00:00", "total": 60, "max_value": 79},
    ]
