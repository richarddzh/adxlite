from __future__ import annotations

from adxlite.parser import parse_kql
from adxlite.translator import SqlTranslator


def _translate(kql: str) -> tuple[str, list[object]]:
    translator = SqlTranslator()
    parsed = parse_kql(kql)
    return translator.translate(parsed)


def test_translator_generates_nested_subqueries_and_parameters() -> None:
    sql, params = _translate("Users | where name == \"Ada\" | take 1")
    assert "SELECT * FROM (SELECT * FROM \"Users\") AS _t WHERE (\"name\" = ?)" in sql
    assert sql.endswith("LIMIT 1")
    assert params == ["Ada"]


def test_translator_handles_summarize_and_sort() -> None:
    sql, params = _translate("Users | summarize total=count(), avg_score=avg(score) by city | sort by total desc")
    assert "COUNT(*) AS \"total\"" in sql
    assert "AVG(\"score\") AS \"avg_score\"" in sql
    assert "GROUP BY \"city\"" in sql
    assert sql.endswith("ORDER BY \"total\" DESC")
    assert params == []


def test_translator_uses_udfs_for_regex_and_datetime() -> None:
    sql, params = _translate("Logs | where Message matches regex \"error\" | extend bucket = bin(ts, 1h)")
    assert "kql_regex_match" in sql
    assert "kql_bin" in sql
    assert params == ["1h", "error"]
