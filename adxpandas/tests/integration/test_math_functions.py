from __future__ import annotations

import math

import pandas as pd
import pytest

from adxpandas import AdxPandasClient


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "T": pd.DataFrame({
            "value": [4.0, 0.0, 9.0, 2.5, None, float("inf")],
            "signed": [-4.0, 0.0, 9.0, -2.5, None, float("inf")],
            "text_num": ["10", "-3", "bad", None, "2.75", "5"],
        })
    })


def test_abs_and_sign_handle_negative_zero_positive_and_infinity() -> None:
    result = _client().query("T | extend magnitude = abs(signed), sign_value = sign(signed) | project magnitude, sign_value")
    assert result.loc[0, "magnitude"] == 4.0
    assert result.loc[0, "sign_value"] == -1
    assert result.loc[1, "sign_value"] == 0
    assert result.loc[2, "sign_value"] == 1
    assert math.isinf(result.loc[5, "magnitude"])


def test_sqrt_handles_zero_and_positive_inputs() -> None:
    result = _client().query("T | where isnotnull(value) and value <= 9 | extend root = sqrt(value) | project value, root | sort by value asc")
    assert result["root"].tolist() == [0.0, math.sqrt(2.5), 2.0, 3.0]


def test_pow_raises_values_to_the_requested_exponent() -> None:
    result = _client().query("T | where value <= 4 | extend squared = pow(value, 2) | project value, squared | sort by value asc")
    assert result["squared"].tolist() == [0.0, 6.25, 16.0]


def test_log_and_log10_return_expected_values_for_positive_inputs() -> None:
    result = _client().query("T | where value in (4.0, 9.0) | extend natural = log(value), decimal = log10(value) | project value, natural, decimal | sort by value asc")
    assert result.loc[0, "natural"] == pytest.approx(math.log(4.0))
    assert result.loc[0, "decimal"] == pytest.approx(math.log10(4.0))
    assert result.loc[1, "natural"] == pytest.approx(math.log(9.0))
    assert result.loc[1, "decimal"] == pytest.approx(math.log10(9.0))


def test_exp_returns_the_expected_power_of_e() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"value": [0.0, 1.0, 2.0]})})
    result = client.query("T | extend raised = exp(value) | project raised")
    assert result["raised"].tolist() == pytest.approx([1.0, math.e, math.exp(2.0)])


def test_floor_ceiling_and_round_apply_expected_rounding_rules() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"signed": [-4.0, 0.0, 9.0, -2.5]})})
    result = client.query("T | extend floored = floor(signed), ceiled = ceiling(signed), rounded = round(signed) | project floored, ceiled, rounded")
    assert result.iloc[0].to_dict() == {"floored": -4.0, "ceiled": -4.0, "rounded": -4.0}
    assert result.iloc[3].to_dict() == {"floored": -3.0, "ceiled": -2.0, "rounded": -2.0}


def test_round_supports_explicit_precision() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"value": [2.345, 2.355]})})
    result = client.query("T | extend rounded = round(value, 2) | project rounded")
    assert result["rounded"].tolist() == [2.35, 2.36]


def test_toint_coerces_invalid_strings_to_null() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"text_num": ["10", "-3", "bad", None]})})
    result = client.query("T | extend converted = toint(text_num) | project converted")
    assert result.loc[0, "converted"] == 10
    assert result.loc[1, "converted"] == -3
    assert pd.isna(result.loc[2, "converted"])
    assert pd.isna(result.loc[3, "converted"])


def test_todouble_parses_numeric_text_values() -> None:
    result = _client().query("T | extend converted = todouble(text_num) | project converted")
    assert result.loc[0, "converted"] == 10.0
    assert result.loc[4, "converted"] == 2.75
    assert pd.isna(result.loc[2, "converted"])


def test_toint_raises_for_fractional_numeric_text() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"text_num": ["2.75"]})})
    with pytest.raises(TypeError, match="cannot safely cast"):
        client.query("T | extend converted = toint(text_num)")


def test_sqrt_raises_for_negative_inputs() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"value": [-1.0]})})
    with pytest.raises(ValueError, match="math domain error"):
        client.query("T | extend root = sqrt(value)")


def test_log_raises_for_zero_inputs() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"value": [0.0]})})
    with pytest.raises(ValueError, match="math domain error"):
        client.query("T | extend natural = log(value)")
