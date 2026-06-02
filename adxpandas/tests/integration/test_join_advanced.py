from __future__ import annotations

import pandas as pd

from adxpandas import AdxPandasClient


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "Sales": pd.DataFrame({
            "k": [1, 2, None, 2],
            "k2": ["a", "b", "c", None],
            "sale": ["s1", "s2", "s3", "s4"],
        }),
        "Events": pd.DataFrame({
            "k": [2, 3, None, 2],
            "k2": ["b", "c", "c", None],
            "event": ["e1", "e2", "e3", "e4"],
        }),
        "Empty": pd.DataFrame({"k": pd.Series(dtype='float64'), "event": pd.Series(dtype='object')}),
    })


def test_inner_join_matches_rows_on_a_single_key() -> None:
    result = _client().query("Sales | join kind=inner (Events) on k | project sale, event | sort by sale asc, event asc")
    assert result.to_dict(orient='records') == [
        {"sale": "s2", "event": "e1"},
        {"sale": "s2", "event": "e4"},
        {"sale": "s3", "event": "e3"},
        {"sale": "s4", "event": "e1"},
        {"sale": "s4", "event": "e4"},
    ]


def test_leftouter_join_preserves_unmatched_left_rows() -> None:
    result = _client().query("Sales | join kind=leftouter (Events) on k | project sale, event | sort by sale asc, event asc")
    assert result.loc[0, "sale"] == "s1"
    assert pd.isna(result.loc[0, "event"])
    assert len(result) == 6


def test_fullouter_join_includes_left_only_and_right_only_rows() -> None:
    result = _client().query("Sales | join kind=fullouter (Events) on k | project sale, event | sort by sale asc, event asc")
    assert len(result) == 7
    assert pd.isna(result.iloc[6]["sale"])
    assert result.iloc[6]["event"] == "e2"


def test_leftanti_join_returns_only_unmatched_left_rows() -> None:
    result = _client().query("Sales | join kind=leftanti (Events) on k | project sale | sort by sale asc")
    assert result["sale"].tolist() == ["s1"]


def test_rightanti_join_returns_only_unmatched_right_rows() -> None:
    result = _client().query("Sales | join kind=rightanti (Events) on k | project event | sort by event asc")
    assert result["event"].tolist() == ["e2"]


def test_leftsemi_join_returns_each_matching_left_row_once() -> None:
    result = _client().query("Sales | join kind=leftsemi (Events) on k | project sale | sort by sale asc")
    assert result["sale"].tolist() == ["s2", "s3", "s4"]


def test_rightsemi_join_returns_each_matching_right_row_once() -> None:
    result = _client().query("Sales | join kind=rightsemi (Events) on k | project event | sort by event asc")
    assert result["event"].tolist() == ["e1", "e3", "e4"]


def test_join_supports_multiple_on_columns_with_left_and_right_notation() -> None:
    result = _client().query("Sales | join kind=inner (Events) on $left.k == $right.k, $left.k2 == $right.k2 | project sale, event | sort by sale asc")
    assert result.to_dict(orient='records') == [
        {"sale": "s2", "event": "e1"},
        {"sale": "s3", "event": "e3"},
        {"sale": "s4", "event": "e4"},
    ]


def test_join_with_an_empty_right_table_returns_no_rows_for_inner_joins() -> None:
    result = _client().query("Sales | join kind=inner (Empty) on k")
    assert result.empty


def test_join_can_use_a_filtered_right_subpipeline() -> None:
    result = _client().query("Sales | join kind=inner (Events | where event != 'e4') on k | project sale, event | sort by sale asc, event asc")
    assert result.to_dict(orient='records') == [
        {"sale": "s2", "event": "e1"},
        {"sale": "s3", "event": "e3"},
        {"sale": "s4", "event": "e1"},
    ]
