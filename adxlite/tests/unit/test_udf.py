from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from adxlite.storage import udf


def test_math_udfs() -> None:
    assert udf.kql_sign(-5) == -1
    assert udf.kql_ceiling(1.2) == 2
    assert round(udf.kql_log10(1000), 5) == 3


def test_regex_udfs() -> None:
    assert udf.kql_regex_match("err..", "prefix error suffix") == 1
    assert udf.kql_regex_extract(r"user=(\w+)", 1, "user=ada") == "ada"


def test_datetime_udfs() -> None:
    binned = udf.kql_bin("2024-01-01T10:45:30", "1h")
    assert binned == "2024-01-01T10:00:00"
    assert udf.kql_datetime_diff("day", "2024-01-03", "2024-01-01") == 2
    formatted = udf.kql_format_datetime("2024-01-01T10:45:30", "yyyy-MM-dd")
    assert formatted == "2024-01-01"


def test_json_udfs() -> None:
    payload = udf.kql_parse_json('{"a": {"b": [1, 2]}}')
    assert json.loads(payload) == {"a": {"b": [1, 2]}}
    assert udf.kql_extractjson("$.a.b[1]", payload) == "2"
