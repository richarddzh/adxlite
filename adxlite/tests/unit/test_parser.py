from __future__ import annotations

from adxlite.parser import parse_kql
from adxlite.parser.ast_nodes import AppendCommand, BinaryOp, FunctionCall, ParseOp, Pipeline, ProjectAwayOp, SortOp, SummarizeOp, WhereOp


def test_parser_builds_pipeline_ast() -> None:
    parsed = parse_kql("Users | where score >= 10 | extend doubled = score * 2 | take 5")
    assert isinstance(parsed, Pipeline)
    assert parsed.source.name == "Users"
    assert isinstance(parsed.operators[0], WhereOp)
    assert isinstance(parsed.operators[0].predicate, BinaryOp)
    assert parsed.operators[0].predicate.operator == ">="
    assert parsed.operators[1].columns[0].alias == "doubled"
    assert parsed.operators[2].count == 5


def test_parser_understands_summarize_and_sort() -> None:
    parsed = parse_kql("Users | summarize total=count(), avg_score=avg(score) by city | sort by total desc")
    summarize = parsed.operators[0]
    sort = parsed.operators[1]
    assert isinstance(summarize, SummarizeOp)
    assert isinstance(summarize.aggregations[0].expr, FunctionCall)
    assert summarize.aggregations[0].alias == "total"
    assert isinstance(sort, SortOp)
    assert sort.keys[0].direction == "desc"


def test_parser_supports_parse_and_project_away() -> None:
    parsed = parse_kql("Logs | parse Message with \"user=\" user \" action=\" action | project-away Message")
    assert isinstance(parsed.operators[0], ParseOp)
    assert [part.value for part in parsed.operators[0].pattern if part.kind == "capture"] == ["user", "action"]
    assert isinstance(parsed.operators[1], ProjectAwayOp)
    assert parsed.operators[1].columns == ("Message",)


def test_parser_supports_append_command() -> None:
    parsed = parse_kql(".append Archive <| Source | where ok == true")
    assert isinstance(parsed, AppendCommand)
    assert parsed.table_name == "Archive"
    assert isinstance(parsed.query, Pipeline)
