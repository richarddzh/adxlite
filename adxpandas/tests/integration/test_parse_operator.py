from __future__ import annotations

import pandas as pd

from adxpandas import AdxPandasClient


def _client() -> AdxPandasClient:
    return AdxPandasClient({
        "Logs": pd.DataFrame({
            "Message": [
                "user=Ada action=login result=ok",
                "user=Alan action=logout result=ok",
                "level=info code=200 text=done",
                "kind[start] id=77",
                "prefix=one middle=two suffix=three",
                "unmatched row",
                "task=backup status=completed with spaces",
                "source=api|name=orders|status=ok",
            ]
        })
    })


def test_parse_extracts_multiple_named_captures() -> None:
    result = _client().query('Logs | parse Message with "user=" user " action=" action " result=" result | where Message startswith "user=" | project user, action, result | sort by user asc')
    assert result.to_dict(orient='records') == [
        {"user": "Ada", "action": "login", "result": "ok"},
        {"user": "Alan", "action": "logout", "result": "ok"},
    ]


def test_parse_supports_wildcard_segments() -> None:
    result = _client().query('Logs | parse Message with "user=" user " action=" * " result=" result | where Message startswith "user=" | project user, result | sort by user asc')
    assert result.to_dict(orient='records') == [
        {"user": "Ada", "result": "ok"},
        {"user": "Alan", "result": "ok"},
    ]


def test_parse_reads_numeric_values_after_literal_separators() -> None:
    result = _client().query('Logs | parse Message with "level=" level " code=" code " text=" text | where Message startswith "level=" | project level, code, text')
    assert result.iloc[0].to_dict() == {"level": "info", "code": "200", "text": "done"}


def test_parse_handles_bracket_literals() -> None:
    result = _client().query('Logs | parse Message with "kind[" kind "] id=" ident | where Message startswith "kind[" | project kind, ident')
    assert result.iloc[0].to_dict() == {"kind": "start", "ident": "77"}


def test_parse_returns_nulls_for_non_matching_rows() -> None:
    result = _client().query('Logs | parse Message with "user=" user " action=" action | where Message == "unmatched row" | project user, action')
    assert pd.isna(result.loc[0, "user"])
    assert pd.isna(result.loc[0, "action"])


def test_parse_uses_a_greedy_final_capture() -> None:
    result = _client().query('Logs | parse Message with "task=" task " status=" status | where Message startswith "task=" | project task, status')
    assert result.iloc[0].to_dict() == {"task": "backup", "status": "completed with spaces"}


def test_parse_handles_multiple_literal_separator_styles() -> None:
    result = _client().query('Logs | parse Message with "source=" source "|name=" name "|status=" status | where Message startswith "source=" | project source, name, status')
    assert result.iloc[0].to_dict() == {"source": "api", "name": "orders", "status": "ok"}


def test_parse_followed_by_project_away_keeps_only_extracted_columns() -> None:
    result = _client().query('Logs | parse Message with "prefix=" prefix " middle=" middle " suffix=" suffix | where Message startswith "prefix=" | project-away Message')
    assert list(result.columns) == ["prefix", "middle", "suffix"]
    assert result.iloc[0].to_dict() == {"prefix": "one", "middle": "two", "suffix": "three"}
