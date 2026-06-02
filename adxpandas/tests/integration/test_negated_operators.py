from __future__ import annotations

import pandas as pd

from adxpandas import AdxPandasClient


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "T": pd.DataFrame({
            "number": [1, 2, 3, None, 5],
            "text": ["alpha beta", "beta", "gamma-end", None, "delta"],
            "amount": [1.5, 2.5, 3.5, None, 5.5],
        })
    })


def test_not_in_on_numbers_keeps_values_outside_the_list() -> None:
    result = _client().query("T | where number not in (2, 5) | project number | sort by number asc")
    assert result["number"].iloc[0:2].tolist() == [1.0, 3.0]
    assert pd.isna(result.iloc[2]["number"])


def test_not_in_on_strings_keeps_non_members() -> None:
    result = _client().query("T | where text not in ('beta', 'delta') | project text | sort by text asc")
    assert result["text"].iloc[0:2].tolist() == ["alpha beta", "gamma-end"]
    assert pd.isna(result.iloc[2]["text"])


def test_not_between_on_numbers_keeps_values_outside_the_range() -> None:
    result = _client().query("T | where number not between (2 .. 4) | project number | sort by number asc")
    assert result["number"].iloc[0:2].tolist() == [1.0, 5.0]
    assert pd.isna(result.iloc[2]["number"])


def test_not_between_on_strings_uses_lexicographic_comparison() -> None:
    result = _client().query("T | where text not between ('beta' .. 'delta') | project text | sort by text asc")
    assert result["text"].iloc[0:2].tolist() == ["alpha beta", "gamma-end"]
    assert pd.isna(result.iloc[2]["text"])


def test_not_has_excludes_rows_with_word_boundary_matches() -> None:
    result = _client().query("T | where text not has 'beta' | project text | sort by text asc")
    assert result["text"].iloc[0:2].tolist() == ["delta", "gamma-end"]
    assert pd.isna(result.iloc[2]["text"])


def test_not_contains_excludes_rows_with_literal_substrings() -> None:
    result = _client().query("T | where text not contains 'end' | project text | sort by text asc")
    assert result["text"].iloc[0:3].tolist() == ["alpha beta", "beta", "delta"]
    assert pd.isna(result.iloc[3]["text"])


def test_not_startswith_excludes_prefix_matches() -> None:
    result = _client().query("T | where text not startswith 'alp' | project text | sort by text asc")
    assert result["text"].iloc[0:3].tolist() == ["beta", "delta", "gamma-end"]
    assert pd.isna(result.iloc[3]["text"])


def test_not_endswith_excludes_suffix_matches() -> None:
    result = _client().query("T | where text not endswith 'end' | project text | sort by text asc")
    assert result["text"].iloc[0:3].tolist() == ["alpha beta", "beta", "delta"]
    assert pd.isna(result.iloc[3]["text"])


def test_multiple_negated_predicates_can_be_combined_with_and() -> None:
    result = _client().query("T | where text not contains 'beta' and text not endswith 'end' | project text | sort by text asc")
    assert result.iloc[0]["text"] == "delta"
    assert pd.isna(result.iloc[1]["text"])
