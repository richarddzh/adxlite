from __future__ import annotations

import pandas as pd
import pytest

from adxpandas import AdxPandasClient
from adxpandas.exceptions import KqlParseError, KqlUnsupportedError, TableNotFoundError


def _client() -> AdxPandasClient:
    return AdxPandasClient({"T": pd.DataFrame({"text": ["a", "b"], "value": [1, 2], "other": [0, 2]})})


def test_invalid_syntax_raises_a_parse_error() -> None:
    with pytest.raises(KqlParseError, match="Unexpected end of query"):
        _client().query("T | where")


def test_missing_tables_raise_table_not_found_errors() -> None:
    with pytest.raises(TableNotFoundError, match="Table 'Missing' not found"):
        _client().query("Missing | count")


def test_missing_columns_raise_key_errors() -> None:
    with pytest.raises(KeyError, match="missing"):
        _client().query("T | where missing > 1")


def test_unsupported_functions_raise_kql_unsupported_errors() -> None:
    with pytest.raises(KqlUnsupportedError, match="Unsupported function 'bag_keys'"):
        _client().query("T | extend keys = bag_keys(text)")


def test_unsupported_operators_raise_kql_unsupported_errors() -> None:
    with pytest.raises(KqlUnsupportedError, match="Unsupported operator 'project-rename'"):
        _client().query("T | project-rename text2=text")


def test_unsupported_aggregations_raise_kql_unsupported_errors() -> None:
    with pytest.raises(KqlUnsupportedError, match="Unsupported aggregation 'percentile'"):
        _client().query("T | summarize value=percentile(value)")


def test_type_mismatches_raise_python_type_errors() -> None:
    with pytest.raises(TypeError, match="concatenate str"):
        _client().query("T | extend mixed = text + value")


def test_division_by_zero_returns_infinity_instead_of_raising() -> None:
    result = _client().query("T | extend ratio = value / other | project ratio")
    assert result["ratio"].tolist() == [float('inf'), 1.0]


def test_empty_in_lists_raise_parse_errors() -> None:
    with pytest.raises(KqlParseError, match="Expected an expression"):
        _client().query("T | where value in ()")


def test_malformed_between_expressions_raise_parse_errors() -> None:
    with pytest.raises(KqlParseError, match="Expected '..' in between expression"):
        _client().query("T | where value between (1 2)")
