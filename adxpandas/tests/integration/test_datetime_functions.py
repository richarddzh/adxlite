from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import pytest

from adxpandas import AdxPandasClient


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "Events": pd.DataFrame({
            "ts": pd.to_datetime(["2024-01-01 10:15:30", "2024-01-01 23:59:59", None, "2024-01-02 12:34:56"]),
            "base": pd.to_datetime(["2024-01-01 00:00:00"] * 4),
            "span": ["2h", "30m", "1d", "15m"],
        })
    })


def test_now_returns_a_parseable_timestamp_close_to_execution_time() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"id": [1]})})
    before = datetime.utcnow()
    result = client.query("T | extend current = now() | project current")
    after = datetime.utcnow()
    current = pd.to_datetime(result.iloc[0]["current"]).to_pydatetime()
    assert before <= current <= after


def test_ago_uses_timespan_values_from_a_column() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"span": ["2h"]})})
    before = datetime.utcnow() - timedelta(hours=2, seconds=2)
    result = client.query("T | extend shifted = ago(span) | project shifted")
    after = datetime.utcnow() - timedelta(hours=2) + timedelta(seconds=2)
    shifted = pd.to_datetime(result.iloc[0]["shifted"]).to_pydatetime()
    assert before <= shifted <= after


def test_bin_rounds_down_to_the_start_of_the_hour() -> None:
    result = _client().query("Events | extend bucket = bin(ts, 1h) | project bucket")
    assert result.loc[0, "bucket"] == "2024-01-01T10:00:00"
    assert result.loc[1, "bucket"] == "2024-01-01T23:00:00"


def test_bin_rounds_down_to_the_start_of_the_day() -> None:
    result = _client().query("Events | extend bucket = bin(ts, 1d) | project bucket")
    assert result.loc[0, "bucket"] == "2024-01-01T00:00:00"
    assert result.loc[3, "bucket"] == "2024-01-02T00:00:00"


def test_datetime_diff_supports_hour_units() -> None:
    result = _client().query("Events | extend diff_hours = datetime_diff('hour', ts, base) | project diff_hours")
    assert result.loc[0, "diff_hours"] == 10.0
    assert result.loc[3, "diff_hours"] == 36.0


def test_datetime_add_offsets_timestamps_by_timespans() -> None:
    result = _client().query("Events | extend shifted = datetime_add(span, ts) | project shifted")
    assert result.loc[0, "shifted"] == "2024-01-01T12:15:30"
    assert result.loc[1, "shifted"] == "2024-01-02T00:29:59"


def test_format_datetime_applies_kql_style_tokens() -> None:
    result = _client().query("Events | extend formatted = format_datetime(ts, 'yyyy/MM/dd HH:mm:ss') | project formatted")
    assert result.loc[0, "formatted"] == "2024/01/01 10:15:30"
    assert result.loc[3, "formatted"] == "2024/01/02 12:34:56"


def test_datetime_functions_return_null_for_null_timestamps() -> None:
    result = _client().query("Events | extend bucket = bin(ts, 1h), formatted = format_datetime(ts, 'yyyy-MM-dd') | project bucket, formatted")
    assert pd.isna(result.loc[2, "bucket"])
    assert pd.isna(result.loc[2, "formatted"])


def test_datetime_diff_rejects_unknown_units() -> None:
    with pytest.raises(ValueError, match="Unsupported datetime_diff unit 'week'"):
        _client().query("Events | extend diff = datetime_diff('week', ts, base)")
