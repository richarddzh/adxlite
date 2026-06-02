from __future__ import annotations

import pandas as pd

from adxlite import AdxLiteClient


def test_datetime_round_trip_and_functions() -> None:
    client = AdxLiteClient()
    dataframe = pd.DataFrame(
        {
            "ts": pd.to_datetime(["2024-01-01T10:05:00", "2024-01-01T11:15:00"]),
            "value": [1, 2],
        }
    )
    client.ingest("Events", dataframe)

    result = client.query(
        'Events | extend bucket = bin(ts, 1h), day_diff = datetime_diff("hour", ts, datetime_add(1h, ts)) | project ts, bucket, day_diff | sort by ts asc'
    )

    assert str(result["ts"].dtype).startswith("datetime64")
    assert result["bucket"].tolist() == ["2024-01-01T10:00:00", "2024-01-01T11:00:00"]
    assert result["day_diff"].tolist() == [-1, -1]
