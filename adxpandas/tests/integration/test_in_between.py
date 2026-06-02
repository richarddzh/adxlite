from __future__ import annotations

import pandas as pd
import pytest

from adxpandas import AdxPandasClient
from adxpandas.exceptions import KqlParseError


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "T": pd.DataFrame({
            "number": [1, 2, 3, None, 5],
            "text": ["alpha", "beta", "gamma", None, "delta"],
            "amount": [1.5, 2.5, 3.5, None, 5.5],
            "code": ["1", "2", "3", None, "5"],
        })
    })


def test_in_matches_integer_values() -> None:
    result = _client().query("T | where number in (1, 3, 5) | project number | sort by number asc")
    assert result["number"].tolist() == [1.0, 3.0, 5.0]


def test_in_matches_string_values() -> None:
    result = _client().query("T | where text in ('alpha', 'delta') | project text | sort by text asc")
    assert result["text"].tolist() == ["alpha", "delta"]


def test_not_in_includes_null_rows_because_the_membership_check_is_false() -> None:
    result = _client().query("T | where number not in (2, 5) | project number | sort by number asc")
    assert result["number"].iloc[0:2].tolist() == [1.0, 3.0]
    assert pd.isna(result.iloc[2]["number"])


def test_between_is_inclusive_for_integers() -> None:
    result = _client().query("T | where number between (2 .. 3) | project number | sort by number asc")
    assert result["number"].tolist() == [2.0, 3.0]


def test_not_between_includes_null_rows_because_between_returns_false_for_nulls() -> None:
    result = _client().query("T | where amount not between (2.0 .. 4.0) | project amount | sort by amount asc")
    assert result["amount"].iloc[0:2].tolist() == [1.5, 5.5]
    assert pd.isna(result.iloc[2]["amount"])


def test_between_supports_string_ranges_using_lexicographic_order() -> None:
    result = _client().query("T | where text between ('beta' .. 'delta') | project text | sort by text asc")
    assert result["text"].tolist() == ["beta", "delta"]


def test_in_can_compare_string_columns_against_mixed_type_lists() -> None:
    result = _client().query("T | where code in ('2', 2, '5') | project code | sort by code asc")
    assert result["code"].tolist() == ["2", "5"]


def test_in_and_between_do_not_match_null_values() -> None:
    result = _client().query("T | where number in (1, 2, 3, 5) or amount between (1.0 .. 6.0) | project number, amount")
    assert len(result) == 4
    assert result["number"].isna().sum() == 0


def test_in_requires_at_least_one_list_value() -> None:
    with pytest.raises(KqlParseError, match="Expected an expression"):
        _client().query("T | where number in ()")
