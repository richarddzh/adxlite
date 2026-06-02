from __future__ import annotations

import pandas as pd
import pytest

from adxpandas import AdxPandasClient
from adxpandas.exceptions import KqlUnsupportedError


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "T": pd.DataFrame({
            "text": [
                "alpha beta",
                "alphabet soup",
                "Error-42 occurred",
                "CaseSensitive",
                "ends.with.dot.",
                "",
                None,
                "Symbols [x] [y]",
            ]
        })
    })


def test_has_matches_whole_words_case_insensitively() -> None:
    result = _client().query("T | where text has 'BETA' | project text")
    assert result["text"].tolist() == ["alpha beta"]


def test_has_does_not_match_partial_words() -> None:
    result = _client().query("T | where text has 'alpha' | project text")
    assert result["text"].tolist() == ["alpha beta"]


def test_not_has_filters_rows_without_whole_word_matches() -> None:
    result = _client().query("T | where text not has 'error' | project text")
    assert "Error-42 occurred" not in result["text"].tolist()
    assert "alphabet soup" in result["text"].tolist()


def test_contains_matches_literal_special_characters() -> None:
    result = _client().query(r"T | where text contains '[x]' | project text")
    assert result["text"].tolist() == ["Symbols [x] [y]"]


def test_not_contains_excludes_matching_rows() -> None:
    result = _client().query("T | where text not contains 'oup' | project text")
    assert "alphabet soup" not in result["text"].tolist()
    assert "alpha beta" in result["text"].tolist()


def test_startswith_matches_prefixes() -> None:
    result = _client().query("T | where text startswith 'Case' | project text")
    assert result["text"].tolist() == ["CaseSensitive"]


def test_not_startswith_keeps_non_matching_rows() -> None:
    result = _client().query("T | where text not startswith 'alpha' | project text")
    assert "alpha beta" not in result["text"].tolist()
    assert "CaseSensitive" in result["text"].tolist()


def test_endswith_matches_suffixes() -> None:
    result = _client().query("T | where text endswith '.' | project text")
    assert result["text"].tolist() == ["ends.with.dot."]


def test_not_endswith_keeps_rows_without_the_suffix() -> None:
    result = _client().query("T | where text not endswith '.' | project text")
    assert "ends.with.dot." not in result["text"].tolist()
    assert "alpha beta" in result["text"].tolist()


def test_contains_treats_empty_string_as_present_in_non_null_rows() -> None:
    result = _client().query("T | where text contains '' | project text")
    assert "alpha beta" in result["text"].tolist()
    assert "" in result["text"].tolist()


def test_has_cs_is_reported_as_unsupported() -> None:
    with pytest.raises(KqlUnsupportedError, match="Unsupported function 'has_cs'"):
        _client().query("T | extend matched = has_cs(text, 'Case')")


def test_contains_cs_is_reported_as_unsupported() -> None:
    with pytest.raises(KqlUnsupportedError, match="Unsupported function 'contains_cs'"):
        _client().query("T | extend matched = contains_cs(text, 'Case')")
