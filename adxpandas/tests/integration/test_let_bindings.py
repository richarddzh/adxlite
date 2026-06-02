from __future__ import annotations

import pandas as pd
import pytest

from adxpandas import AdxPandasClient
from adxpandas.exceptions import ExecutionError


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "T": pd.DataFrame({
            "value": [10, 20, 30, 40],
            "text": ["alpha", "beta", "gamma", "beta"],
        })
    })


def test_scalar_let_filters_numeric_rows() -> None:
    result = _client().query("let threshold = 20; T | where value > threshold | project value | sort by value asc")
    assert result["value"].tolist() == [30, 40]


def test_scalar_let_can_reference_previous_scalar_lets() -> None:
    result = _client().query("let base = 10; let limit = base * 3; T | where value >= limit | project value | sort by value asc")
    assert result["value"].tolist() == [30, 40]


def test_scalar_string_let_can_be_used_in_filters() -> None:
    result = _client().query("let target = 'beta'; T | where text == target | project value | sort by value asc")
    assert result["value"].tolist() == [20, 40]


def test_scalar_let_supports_unary_minus() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"value": [-10, 0, 10]})})
    result = client.query("let floor_value = -5; T | where value < floor_value | project value")
    assert result["value"].tolist() == [-10]


def test_scalar_division_by_zero_falls_back_to_zero() -> None:
    result = _client().query("let ratio = 10 / 0; T | where value > ratio | count")
    assert result.iloc[0]["Count"] == 4


def test_tabular_let_can_store_a_filtered_pipeline() -> None:
    result = _client().query("let big = T | where value >= 30; big | summarize total=count(), top=max(value)")
    assert result.iloc[0].to_dict() == {"total": 2, "top": 40}


def test_tabular_let_cannot_reference_scalar_lets_during_materialization() -> None:
    with pytest.raises(KeyError, match="threshold"):
        _client().query("let threshold = 15; let filtered = T | where value > threshold; filtered | summarize total=count()")


def test_tabular_lets_can_reference_other_tabular_lets() -> None:
    result = _client().query("let filtered = T | where value >= 20; let winners = filtered | top 2 by value desc; winners | project value | sort by value asc")
    assert result["value"].tolist() == [30, 40]


def test_scalar_let_raises_for_undefined_references() -> None:
    with pytest.raises(ExecutionError, match="Undefined reference 'missing'"):
        _client().query("let threshold = missing; T | where value > 0")


def test_scalar_let_rejects_complex_function_expressions() -> None:
    with pytest.raises(ExecutionError, match="Scalar let values must be literals"):
        _client().query("let threshold = toint('10'); T | where value > threshold")
