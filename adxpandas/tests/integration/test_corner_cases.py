from __future__ import annotations

import pandas as pd

from adxpandas import AdxPandasClient


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "T": pd.DataFrame({
            "value": [1.0, None, 3.0],
            "text": ["alpha", "", None],
            "flag": [True, None, False],
        })
    })


def test_count_on_an_empty_table_returns_zero() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"value": pd.Series(dtype='float64'), "text": pd.Series(dtype='object')})})
    result = client.query("T | count")
    assert result.iloc[0]["Count"] == 0


def test_project_on_an_empty_filtered_table_preserves_column_names() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"value": pd.Series(dtype='float64'), "text": pd.Series(dtype='object')})})
    result = client.query("T | where value > 0 | project value, text")
    assert result.empty
    assert list(result.columns) == ["value", "text"]


def test_single_row_tables_support_basic_arithmetic_pipelines() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"value": [5]})})
    result = client.query("T | extend doubled = value * 2 | project doubled")
    assert result.iloc[0]["doubled"] == 10


def test_extend_with_duplicate_aliases_applies_updates_sequentially() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"value": [1]})})
    result = client.query("T | extend value = value + 1, value = value + 10 | project value")
    assert result.iloc[0]["value"] == 12


def test_iif_supports_scalar_branch_values() -> None:
    result = _client().query("T | extend bucket = iif(value > 1, 'big', 'small') | project bucket")
    assert result["bucket"].tolist() == ["small", "small", "big"]


def test_iff_treats_null_conditions_as_false() -> None:
    result = _client().query("T | extend label = iff(flag, 'yes', 'no') | project label")
    assert result["label"].tolist() == ["yes", "no", "no"]


def test_coalesce_uses_scalar_fallback_values() -> None:
    result = _client().query("T | extend filled = coalesce(text, 'fallback') | project filled")
    assert result["filled"].tolist() == ["alpha", "", "fallback"]


def test_isnull_and_isnotnull_identify_missing_values() -> None:
    result = _client().query("T | extend missing = isnull(value), present = isnotnull(value) | project missing, present")
    assert result["missing"].tolist() == [False, True, False]
    assert result["present"].tolist() == [True, False, True]


def test_isempty_and_isnotempty_treat_empty_strings_and_nulls_as_empty() -> None:
    result = _client().query("T | extend empty = isempty(text), not_empty = isnotempty(text) | project empty, not_empty")
    assert result["empty"].tolist() == [False, True, True]
    assert result["not_empty"].tolist() == [True, False, False]
