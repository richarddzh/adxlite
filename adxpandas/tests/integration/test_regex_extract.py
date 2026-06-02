from __future__ import annotations

import pandas as pd
import pytest

from adxpandas import AdxPandasClient


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "Logs": pd.DataFrame({
            "Message": [
                "id=42 status=ok",
                "path=/api/v1/items/17",
                "price=$19.95",
                "date=2024-01-31",
                "user:ada email=ada@example.com",
                "no-digits",
                None,
                "literal a+b*c",
            ]
        })
    })


def test_extract_returns_group_zero_for_the_full_match() -> None:
    result = _client().query(r"Logs | extend value = extract('(id=\d+)', 1, Message) | where Message startswith 'id=' | project value")
    assert result.iloc[0]["value"] == "id=42"


def test_extract_returns_requested_capture_group() -> None:
    result = _client().query(r"Logs | extend value = extract('id=(\d+) status=(\w+)', 2, Message) | where Message startswith 'id=' | project value")
    assert result.iloc[0]["value"] == "ok"


def test_extract_returns_none_when_there_is_no_match() -> None:
    result = _client().query(r"Logs | extend value = extract('(\d+)', 1, Message) | where Message == 'no-digits' | project value")
    assert pd.isna(result.iloc[0]["value"])


def test_extract_handles_special_regex_characters() -> None:
    result = _client().query(r"Logs | extend value = extract('\$(\d+\.\d+)', 1, Message) | where Message startswith 'price=' | project value")
    assert result.iloc[0]["value"] == "19.95"


def test_extract_handles_nested_path_patterns() -> None:
    result = _client().query(r"Logs | extend value = extract('/api/v(\d+)/items/(\d+)', 2, Message) | where Message startswith 'path=' | project value")
    assert result.iloc[0]["value"] == "17"


def test_extract_supports_complex_date_patterns() -> None:
    result = _client().query(r"Logs | extend value = extract('(\d{4})-(\d{2})-(\d{2})', 3, Message) | where Message startswith 'date=' | project value")
    assert result.iloc[0]["value"] == "31"


def test_extract_returns_none_for_null_inputs() -> None:
    result = _client().query(r"Logs | extend value = extract('(\d+)', 1, Message) | project value")
    assert pd.isna(result.loc[6, "value"])


def test_extract_can_capture_email_usernames() -> None:
    result = _client().query(r"Logs | extend value = extract('email=([^@]+)@', 1, Message) | where Message contains 'email=' | project value")
    assert result.iloc[0]["value"] == "ada"


def test_extract_treats_literal_plus_and_star_as_regex_tokens() -> None:
    result = _client().query(r"Logs | extend value = extract('a\+b\*c', 0, Message) | where Message contains 'literal' | project value")
    assert result.iloc[0]["value"] == "a+b*c"


def test_extract_raises_index_error_for_missing_capture_group() -> None:
    with pytest.raises(IndexError, match="no such group"):
        _client().query(r"Logs | extend value = extract('(id=(\d+))', 3, Message)")
