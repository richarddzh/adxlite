from __future__ import annotations

import json

import pandas as pd
import pytest

from adxpandas import AdxPandasClient
from adxpandas.exceptions import KqlUnsupportedError


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "T": pd.DataFrame({
            "text": [" Alpha ", "", None, "naïve café", "abc--def", "abcabc", "边界", "  spaced  "],
        })
    })


def test_strlen_handles_empty_unicode_and_null_values() -> None:
    result = _client().query("T | extend length = strlen(text) | project text, length")
    # Non-null rows should have correct lengths
    assert result.loc[0, "length"] == 7.0
    assert result.loc[1, "length"] == 0.0
    assert result.loc[3, "length"] == 10.0
    assert result.loc[4, "length"] == 8.0
    assert result.loc[5, "length"] == 6.0
    assert result.loc[6, "length"] == 2.0
    assert result.loc[7, "length"] == 10.0


def test_substring_supports_negative_start_indexes() -> None:
    result = _client().query("T | extend tail = substring(text, -3, 2) | project text, tail")
    # Check non-null rows for expected substrings
    non_null = result[result["text"].notna()]
    assert non_null.iloc[0]["tail"] == "ha"   # " Alpha " -> index -3 is "ha"
    assert non_null.iloc[3]["tail"] == "de"   # "abc--def"
    assert non_null.iloc[4]["tail"] == "ab"   # "abcabc"
    assert non_null.iloc[5]["tail"] == "边"   # "边界"


def test_substring_returns_empty_string_when_start_is_past_end() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"text": [" Alpha ", "", "hello"]})})
    result = client.query("T | extend piece = substring(text, 100, 5) | project piece")
    assert result.loc[0, "piece"] == ""
    assert result.loc[1, "piece"] == ""
    assert result.loc[2, "piece"] == ""


def test_strcat_concatenates_columns_and_literals() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"text": [" Alpha ", "abc--def", "hello"]})})
    result = client.query("T | extend joined = strcat(text, '::', 'done') | project joined")
    assert result.loc[0, "joined"] == " Alpha ::done"
    assert result.loc[1, "joined"] == "abc--def::done"
    assert result.loc[2, "joined"] == "hello::done"


def test_split_supports_multi_character_delimiters() -> None:
    result = _client().query("T | extend parts = split(text, '--') | where text == 'abc--def' | project parts")
    assert json.loads(result.iloc[0]["parts"]) == ["abc", "def"]


def test_split_with_empty_delimiter_returns_each_character() -> None:
    result = _client().query("T | extend chars = split(text, '') | where text == '边界' | project chars")
    assert json.loads(result.iloc[0]["chars"]) == ["边", "界"]


def test_replace_string_replaces_all_occurrences() -> None:
    result = _client().query("T | extend replaced = replace_string(text, 'ab', 'XY') | where text == 'abcabc' | project replaced")
    assert result.iloc[0]["replaced"] == "XYcXYc"


def test_trim_strips_whitespace_and_custom_characters() -> None:
    client = AdxPandasClient({"T": pd.DataFrame({"text": ["  hello  ", "--value--"]})})
    result = client.query("T | extend plain = trim(text), custom = trim('-', text) | project plain, custom")
    assert result.iloc[0].to_dict() == {"plain": "hello", "custom": "  hello  "}
    assert result.iloc[1].to_dict() == {"plain": "--value--", "custom": "value"}


def test_tolower_and_toupper_preserve_unicode_characters() -> None:
    result = _client().query("T | extend lower = tolower(text), upper = toupper(text) | where text == 'naïve café' | project lower, upper")
    assert result.iloc[0].to_dict() == {"lower": "naïve café", "upper": "NAÏVE CAFÉ"}


def test_indexof_returns_negative_one_when_substring_is_missing() -> None:
    result = _client().query("T | extend pos = indexof(text, '--') | project text, pos")
    assert result.loc[4, "pos"] == 3
    assert list(result["pos"].iloc[[0, 1, 3, 5, 6, 7]]) == [-1, -1, -1, -1, -1, -1]


def test_countof_counts_non_overlapping_occurrences() -> None:
    result = _client().query("T | extend hits = countof(text, 'ab') | where text == 'abcabc' | project hits")
    assert result.iloc[0]["hits"] == 2


def test_reverse_reverses_unicode_text() -> None:
    result = _client().query("T | extend flipped = reverse(text) | where text == '边界' | project flipped")
    assert result.iloc[0]["flipped"] == "界边"


def test_trim_start_is_reported_as_unsupported() -> None:
    with pytest.raises(KqlUnsupportedError, match="Unsupported function 'trim_start'"):
        _client().query("T | extend value = trim_start(text)")


def test_trim_end_is_reported_as_unsupported() -> None:
    with pytest.raises(KqlUnsupportedError, match="Unsupported function 'trim_end'"):
        _client().query("T | extend value = trim_end(text)")
