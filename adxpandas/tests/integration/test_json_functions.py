from __future__ import annotations

import json

import pandas as pd
import pytest

from adxpandas import AdxPandasClient
from adxpandas.exceptions import KqlUnsupportedError


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "Events": pd.DataFrame({
            "payload": [
                '{"user":{"name":"Ada","roles":["admin","reader"]},"count":2}',
                '{"items":[10,20,30],"meta":{"ok":true}}',
                '{"nested":{"child":{"value":"x"}}}',
            ]
        })
    })


def test_parse_json_normalizes_object_text() -> None:
    result = _client().query("Events | extend parsed = parse_json(payload) | where payload contains 'count' | project parsed")
    assert json.loads(result.iloc[0]["parsed"]) == {"user": {"name": "Ada", "roles": ["admin", "reader"]}, "count": 2}


def test_dynamic_alias_matches_parse_json_behavior() -> None:
    result = _client().query("Events | extend parsed = dynamic(payload) | where payload contains 'items' | project parsed")
    assert json.loads(result.iloc[0]["parsed"]) == {"items": [10, 20, 30], "meta": {"ok": True}}


def test_parse_json_raises_when_series_contains_null_values() -> None:
    client = AdxPandasClient({"Events": pd.DataFrame({"payload": ['{"ok": true}', None]})})
    with pytest.raises(json.JSONDecodeError):
        client.query("Events | extend parsed = parse_json(payload)")


def test_parse_json_raises_on_invalid_json_text() -> None:
    client = AdxPandasClient({"Events": pd.DataFrame({"payload": ["not-json"]})})
    with pytest.raises(json.JSONDecodeError):
        client.query("Events | extend parsed = parse_json(payload)")


def test_extractjson_reads_nested_object_fields() -> None:
    result = _client().query(r"Events | extend name = extractjson('$.user.name', payload) | where payload contains 'roles' | project name")
    assert result.iloc[0]["name"] == "Ada"


def test_extractjson_reads_array_elements() -> None:
    result = _client().query(r"Events | extend item = extractjson('$.items[1]', payload) | where payload contains 'items' | project item")
    assert result.iloc[0]["item"] == "20"


def test_extractjson_returns_json_strings_for_nested_objects() -> None:
    result = _client().query(r"Events | extend child = extractjson('$.nested.child', payload) | where payload contains 'nested' | project child")
    assert json.loads(result.iloc[0]["child"]) == {"value": "x"}


def test_extractjson_returns_null_for_missing_paths() -> None:
    result = _client().query(r"Events | extend missing = extractjson('$.user.id', payload) | where payload contains 'roles' | project missing")
    assert pd.isna(result.iloc[0]["missing"])


def test_extractjson_returns_null_for_invalid_json_text() -> None:
    client = AdxPandasClient({"Events": pd.DataFrame({"payload": ["not-json"]})})
    result = client.query(r"Events | extend value = extractjson('$.user', payload) | project value")
    assert pd.isna(result.iloc[0]["value"])


def test_bag_keys_is_reported_as_unsupported() -> None:
    with pytest.raises(KqlUnsupportedError, match="Unsupported function 'bag_keys'"):
        _client().query("Events | extend keys = bag_keys(payload)")


def test_array_length_is_reported_as_unsupported() -> None:
    with pytest.raises(KqlUnsupportedError, match="Unsupported function 'array_length'"):
        _client().query("Events | extend size = array_length(payload)")
